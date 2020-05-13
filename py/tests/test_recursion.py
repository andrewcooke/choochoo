from logging import getLogger

from sqlalchemy import Column, Integer, ForeignKey, create_engine, union
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql.functions import count

from tests import LogTestCase


log = getLogger(__name__)
Base = declarative_base()


'''
the idea here is that we have some nodes in a 'directed graph'.  that means that some nodes
are the 'input' to other nodes.  that relationship is described in the connect table, which 
has an entry for each connection.

in addition, each node has a required number of inputs.  the problem, then, is to detect when
this is inconsistent with the actual number of inputs.

we can solve that problem directly with a normal SQL query.  however, when we delete nodes 
that are inconsistent we can introduce more problems with other nodes.  to delete all nodes
and leave a consistent graph we need a recursive query.

this problem may seem a little contrived.  the motivation is tracking the provenance of
calculated data in choochoo - some statistics may be calculated from multiple sources and
we need to detect which statistics become invalid when some sources are deleted.  that
kind of problem can often be solved with 'on delete cascade', but in the case of choochoo
it is complicated by 'table inheritance' (inheritance in the OO model mapped to the 
database).  the end result is that we need to do this 'garbage collection' manually.  
'''


class Node(Base):

    __tablename__ = 'node'

    id = Column(Integer, primary_key=True)
    n_input = Column(Integer, nullable=False)


class Connect(Base):

    __tablename__ = 'connect'

    id = Column(Integer, primary_key=True)
    input_id = Column(Integer, ForeignKey('node.id', ondelete='cascade'), nullable=False)
    input = relationship('Node', foreign_keys=[input_id])
    output_id = Column(Integer, ForeignKey('node.id', ondelete='cascade'), nullable=False)
    output = relationship('Node', foreign_keys=[output_id])


class RecursiveTest(LogTestCase):

    def setUp(self):
        super().setUp()
        self.engine = create_engine('sqlite:///:memory:', echo=True)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        '''
        construct the following graph:
        
        1 --\ 
            > 3 --> 5 -\
        2 --/            > 7 --> 8 
              4     6 -/
              
        note that 4 is not connected to anything and that 5 has only one input, when it expects 2
        (not shown in the diagram above, but set below).
        
        this means that node 5 is inconsistent.  removing that would make node 7 inconsistent and
        removing that would make node 8 inconsistent.  so we want a query that finds (and allows us
        to delete) nodes 5, 7 and 8. 
        '''

        for i in range(8):
            self.session.add(Node(n_input=0))
        self.session.add(Connect(input_id=1, output_id=3))
        self.session.add(Connect(input_id=2, output_id=3))
        self.session.query(Node).filter(Node.id == 3).one().n_input = 2
        self.session.add(Connect(input_id=3, output_id=5))
        self.session.query(Node).filter(Node.id == 5).one().n_input = 2  # wrong!  3 is not an input to 4
        self.session.add(Connect(input_id=5, output_id=7))
        self.session.add(Connect(input_id=6, output_id=7))
        self.session.query(Node).filter(Node.id == 7).one().n_input = 2
        self.session.add(Connect(input_id=7, output_id=8))
        self.session.query(Node).filter(Node.id == 8).one().n_input = 1
        self.session.flush()

    def test_non_zero_inputs(self):
        '''
        the most simple query i can think of, which returns the number of inputs for nodes
        with more than one input
        '''
        q_n_inputs = self.session.query(Connect.output_id.label('id'), count(Connect.input_id).label('count')). \
            group_by(Connect.output_id).order_by(Connect.output_id)
        self.assertEqual([(3, 2), (5, 1), (7, 2), (8, 1)], q_n_inputs.all())

    def test_all_inputs(self):
        '''
        we can improve th eabove to include nodes with zero inputs.
        '''
        q_n_inputs = self.session.query(Node.id.label('id'), count(Connect.input_id).label('count')). \
            outerjoin(Connect, Node.id == Connect.output_id). \
            group_by(Node.id).order_by(Node.id)
        print(q_n_inputs)
        self.assertEqual([(1, 0), (2, 0), (3, 2), (4, 0), (5, 1), (6, 0), (7, 2), (8, 1)], q_n_inputs.all())

    def test_missing_input(self):
        '''
        using the query above as a sub-query, we can compare the actual number of inputs with
        what was expected and find nodes with missing inputs.
        '''
        q_n_inputs = self.session.query(Node.id.label('id'), count(Connect.input_id).label('count')). \
            outerjoin(Connect, Node.id == Connect.output_id). \
            group_by(Node.id).order_by(Node.id).subquery()
        q_missing = self.session.query(Node.id.label('id')). \
            join(q_n_inputs, q_n_inputs.c.id == Node.id). \
            filter(Node.n_input != q_n_inputs.c.count).order_by(Node.id)
        print(q_missing)
        self.assertEqual([(5,)], q_missing.all())

    def test_chained_node(self):
        '''
        we can move one step along the chain by looking for nodes whose inputs will be deleted.
        '''
        q_counts = self.session.query(Node.id.label('id'), count(Connect.input_id).label('count')). \
            outerjoin(Connect, Node.id == Connect.output_id). \
            group_by(Node.id).order_by(Node.id).subquery()
        q_missing = self.session.query(Node.id.label('id')). \
            join(q_counts, q_counts.c.id == Node.id). \
            filter(Node.n_input != q_counts.c.count)
        q_chained = self.session.query(Node.id). \
            join(Connect, Node.id == Connect.output_id). \
            filter(Connect.input_id.in_(q_missing))
        q_all = union(q_missing, q_chained)
        print('\nchained node\n%s\n' % q_all.select())
        self.assertEqual([(5,), (7,)],
                         self.session.query(Node.id).filter(Node.id.in_(q_all.select())).order_by(Node.id).all())

    def test_recursive(self):
        '''
        but to get all nodes we need to recurse...
        '''
        q_counts = self.session.query(Node.id.label('id'), count(Connect.input_id).label('count')). \
            outerjoin(Connect, Node.id == Connect.output_id). \
            group_by(Node.id).order_by(Node.id).subquery()
        q_missing = self.session.query(Node.id.label('id')). \
            join(q_counts, q_counts.c.id == Node.id). \
            filter(Node.n_input != q_counts.c.count).cte(recursive=True)
        q_missing = q_missing.union_all(self.session.query(Node.id).
                                        join(Connect, Node.id == Connect.output_id).
                                        join(q_missing, Connect.input_id == q_missing.c.id))
        print('\nrecursive\n%s\n' % q_missing.select())
        self.assertEqual([(5,), (7,), (8,)],
                         self.session.query(Node.id).filter(Node.id.in_(q_missing.select())).order_by(Node.id).all())
        # this part of test assumes this test runs last in case (since nodes are deleted)
        # self.session.query(Node).filter(Node.id.in_(q_missing.select())).delete(synchronize_session=False)
        # self.session.flush()
        # self.assertEqual([(1,), (2,), (3,), (4,), (6,)], self.session.query(Node.id).order_by(Node.id).all())

    def test_bug(self):
        '''
        so why does this work, without 'recursive'?

        EDIT: the 'recursive' is optional in sqlite!  see the very last line at
        https://www.sqlite.org/lang_with.html

        damn.  and all that trouble to make a nice bug report.
        '''
        q_counts = self.session.query(Node.id.label('id'), count(Connect.input_id).label('count')). \
            outerjoin(Connect, Node.id == Connect.output_id). \
            group_by(Node.id).order_by(Node.id).subquery()
        q_missing = self.session.query(Node.id.label('id')). \
            join(q_counts, q_counts.c.id == Node.id). \
            filter(Node.n_input != q_counts.c.count).cte()
        q_missing = q_missing.union_all(self.session.query(Node.id).
                                        join(Connect, Node.id == Connect.output_id).
                                        join(q_missing, Connect.input_id == q_missing.c.id))
        print('\nbug\n%s\n' % q_missing.select())
        self.assertEqual([(5,), (7,), (8,)],
                         self.session.query(Node.id).filter(Node.id.in_(q_missing.select())).order_by(Node.id).all())

    def test_dump(self):
        cnx = self.engine.raw_connection()
        for line in cnx.iterdump():
            print(line)

'''
bug report details:

BEGIN TRANSACTION;
CREATE TABLE connect (
	id INTEGER NOT NULL, 
	input_id INTEGER NOT NULL, 
	output_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(input_id) REFERENCES node (id) ON DELETE cascade, 
	FOREIGN KEY(output_id) REFERENCES node (id) ON DELETE cascade
);
INSERT INTO "connect" VALUES(1,1,3);
INSERT INTO "connect" VALUES(2,2,3);
INSERT INTO "connect" VALUES(3,3,5);
INSERT INTO "connect" VALUES(4,5,7);
INSERT INTO "connect" VALUES(5,6,7);
INSERT INTO "connect" VALUES(6,7,8);
CREATE TABLE node (
	id INTEGER NOT NULL, 
	n_input INTEGER NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "node" VALUES(1,0);
INSERT INTO "node" VALUES(2,0);
INSERT INTO "node" VALUES(3,2);
INSERT INTO "node" VALUES(4,0);
INSERT INTO "node" VALUES(5,2);
INSERT INTO "node" VALUES(6,0);
INSERT INTO "node" VALUES(7,2);
INSERT INTO "node" VALUES(8,1);
COMMIT;

  WITH RECURSIVE anon_1(id) 
    AS (SELECT node.id AS id 
          FROM node 
          JOIN (SELECT node.id AS id, 
                       count(connect.input_id) AS count 
                  FROM node 
                  LEFT OUTER JOIN connect 
                    ON node.id = connect.output_id 
                 GROUP BY node.id ORDER BY node.id) 
            AS anon_2 
            ON anon_2.id = node.id 
         WHERE node.n_input != anon_2.count 
         UNION ALL 
        SELECT node.id AS node_id 
          FROM node 
          JOIN connect 
            ON node.id = connect.output_id 
          JOIN anon_1 
            ON connect.input_id = anon_1.id)
SELECT node.id AS node_id 
  FROM node 
 WHERE node.id 
    IN (SELECT anon_1.id 
          FROM anon_1)
 ORDER BY node.id;

% 5 7 8

  WITH anon_1 
    AS (SELECT node.id AS id 
          FROM node 
          JOIN (SELECT node.id AS id, 
                       count(connect.input_id) AS count 
                  FROM node 
                  LEFT OUTER JOIN connect 
                    ON node.id = connect.output_id 
                 GROUP BY node.id 
                 ORDER BY node.id) 
            AS anon_2 
            ON anon_2.id = node.id 
         WHERE node.n_input != anon_2.count 
         UNION ALL 
        SELECT node.id AS node_id 
          FROM node 
          JOIN connect 
            ON node.id = connect.output_id 
          JOIN anon_1 
            ON connect.input_id = anon_1.id)
SELECT node.id AS node_id 
  FROM node 
 WHERE node.id 
    IN (SELECT anon_1.id 
          FROM anon_1) 
 ORDER BY node.id;
 
% 5 7 8
'''