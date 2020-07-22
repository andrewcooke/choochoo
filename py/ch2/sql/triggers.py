from sqlalchemy import DDL
from sqlalchemy.event import listen


def initial_ddl():
    '''
    Define the function used to raise an exception to protect from deleting child rows directly.
    '''
    # double % below is to avoid sqlalchemy interpolation for DDL
    return DDL('''
create function refuse_child() returns trigger as $$
  begin
    raise 'Attempt to delete from child table %%', TG_TABLE_NAME;
  end;
$$ language plpgsql;
''')


def child_ddl(parent, child, identity):
    '''
    Remove the existing foreign key with constraint and add one without cascade.
    Then re-implement the cascade, but restricting to the correct child table (only).
    Finally, add a warning to catch direct deletion of child tables
    (I did try a reverse cascade, but it causes problems with circular invocation).

    Assumes primary key is called 'id' in both tables, that the discriminator is called 'type',
    and that the existing foreign key constraint is called {child}_id_fkey.

    Note 'before' for child cascades to avoid foreign key conflict.
    '''
    return DDL(f'''
alter table "{child}" drop constraint "{child}_id_fkey";
alter table "{child}" add constraint "{child}_id_fkey"
  foreign key (id) references "{parent}"(id);
create function "{child}_cascade"() returns trigger as $$
  begin
    delete from "{child}" where id = old.id;
    return old;
  end
$$ language plpgsql;
 create trigger "{child}_cascade_trg"
 before delete on "{parent}"
    for each row
   when (old.type = {identity})
execute procedure "{child}_cascade"();
 create trigger "{child}_protect_trg"
 before delete on "{child}"
   when (pg_trigger_depth() = 0)
execute procedure refuse_child();
''')


def add_child_ddl(parent_table):

    parent = parent_table.__tablename__

    def decorator(child_table):
        child = child_table.__tablename__
        identity = child_table.__mapper_args__['polymorphic_identity']
        listen(child_table.__table__, 'after_create',
               child_ddl(parent, child, identity).
               execute_if(dialect='postgresql'))
        return child_table

    return decorator
