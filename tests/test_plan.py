
from choochoo.args import parser, NamespaceWithVariables
from choochoo.log import make_log
from choochoo.plan.british import twelve_week_improver
from choochoo.plan.exponential import exponential_time, exponential_distance
from choochoo.squeal.database import Database
from choochoo.squeal.tables.schedule import Schedule, ScheduleDiary


def test_british():
    plan = twelve_week_improver('2018-07-25')
    p = parser()
    args = NamespaceWithVariables(p.parse_args(['--database', ':memory:', 'add-plan']))
    log = make_log(args)
    db = Database(args, log)
    with db.session_context() as session:
        plan.create(log, session)
        session.flush()
    root = session.query(Schedule).filter(Schedule.parent_id == None).one()
    assert len(root.children) == 7, root.children
    for child in root.children:
        print(child)


def test_exponential_time():
    plan = exponential_time('Time test', '2d', '20m', '5', '2018-07-25', '1M')
    p = parser()
    args = NamespaceWithVariables(p.parse_args(['--database', ':memory:', 'add-plan']))
    log = make_log(args)
    db = Database(args, log)
    with db.session_context() as session:
        plan.create(log, session)
        session.flush()
    schedule = session.query(Schedule).filter(Schedule.parent_id == None).one()
    notes = session.query(ScheduleDiary).filter(ScheduleDiary.schedule == schedule).all()
    assert len(notes) == 16, len(notes)
    for note in notes:
        print(note)


def test_exponential_distance():
    plan = exponential_distance('Distance test', 'w[mon,wed,fri]', '20km', '5', '2018-07-25', '1M')
    p = parser()
    args = NamespaceWithVariables(p.parse_args(['--database', ':memory:', 'add-plan']))
    log = make_log(args)
    db = Database(args, log)
    with db.session_context() as session:
        plan.create(log, session)
        session.flush()
    schedule = session.query(Schedule).filter(Schedule.parent_id == None).one()
    notes = session.query(ScheduleDiary).filter(ScheduleDiary.schedule == schedule).all()
    assert len(notes) == 14, len(notes)
    for note in notes:
        print(note)
