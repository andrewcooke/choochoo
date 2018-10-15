
from tempfile import NamedTemporaryFile

from ch2.command.args import bootstrap_file, m, V, mm, DEV
from ch2.config.default import default
from ch2.config.plan.british import twelve_week_improver
from ch2.config.plan.exponential import exponential_time, exponential_distance
from ch2.lib.date import to_date, add_date
from ch2.squeal.tables.topic import Topic


def test_british():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        plan = twelve_week_improver('2018-07-25')
        plan.create(log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            root = s.query(Topic).filter(Topic.parent_id == None, Topic.name == 'Plan').one()
            assert len(root.children) == 1, root.children
            assert root.schedule
            assert root.schedule.start == to_date('2018-07-25'), root.schedule.start
            assert root.schedule.finish == add_date('2018-07-25', (12, 'w')), root.schedule.finish
            parent = root.children[0]
            assert len(parent.children) == 7, parent.children
            for child in parent.children:
                print(child)


def test_exponential_time():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        plan = exponential_time('Time test', '2d[2]', '20M', 5, '2018-07-25', '3m')
        plan.create(log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            root = s.query(Topic).filter(Topic.parent_id == None, Topic.name == 'Plan').one()
            assert len(root.children) == 1, root.children
            parent = root.children[0]
            assert len(parent.children) == 46, len(parent.children)
            for child in parent.children:
                print(child)


def test_exponential_distance():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        plan = exponential_distance('Distance test', 'w[mon,wed,fri]', '20km', 5, '2018-07-25', '1m')
        plan.create(log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            root = s.query(Topic).filter(Topic.parent_id == None, Topic.name == 'Plan').one()
            assert len(root.children) == 1, root.children
            parent = root.children[0]
            assert len(parent.children) == 14, len(parent.children)
            for child in parent.children:
                print(child)
