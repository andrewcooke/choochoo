
from tempfile import NamedTemporaryFile

from sqlalchemy.sql.functions import count

from ch2.command.activities import activities
from ch2.command.args import bootstrap_file, m, V, DEV, mm, FAST, F
from ch2.command.constants import constants
from ch2.config.default import default
from ch2.data import data
from ch2.squeal.tables.activity import ActivityJournal
from ch2.squeal.tables.pipeline import PipelineType
from ch2.squeal.tables.statistic import StatisticJournal
from ch2.stoats.calculate import run_pipeline_after


def test_activities():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5')

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        args, log, db = bootstrap_file(f, m(V), '5', 'constants', '--set', 'FTHR.%', '154')
        constants(args, log, db)

        args, log, db = bootstrap_file(f, m(V), '5', 'constants', 'FTHR.%')
        constants(args, log, db)

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                       'activities', mm(FAST), 'data/test/personal/2018-08-27-rec.fit')
        activities(args, log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_pipeline_after(log, db, PipelineType.STATISTIC, force=True, after='2018-01-01')

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            n = s.query(count(StatisticJournal.id)).scalar()
            # assert n == 10530, n
            assert n == 14698, n
            journal = s.query(ActivityJournal).one()
            assert journal.start != journal.finish


def import_activity(f):
    bootstrap_file(f, m(V), '0', mm(DEV), configurator=default)
    args, log, db = bootstrap_file(f, m(V), '0', 'constants', '--set', 'FTHR.%', '154')
    constants(args, log, db)
    args, log, db = bootstrap_file(f, m(V), '0', mm(DEV),
                                   'activities', 'data/test/personal/2018-08-27-rec.fit')
    activities(args, log, db)


def test_activity():
    with NamedTemporaryFile() as f:
        import_activity(f)
        # there's a bokeh version of this in the notebooks
        d = data(m(V), '0', mm(DEV), m(F), f.name)
        activity_groups = d.activity_groups()
        print(activity_groups)
        statistic_names = d.statistic_names()
        print(statistic_names)
        journals = d.statistic_journals('Active %')
        print(journals)
        # run('sqlite3 %s ".dump"' % f.name, shell=True)


# below assumes data in the local DB

# def test_activities():
#     d = data()
#     frame = d.statistic_journals('Active Distance')
#     print(frame)
#     fig, ax = plt.subplots()
#     plt.scatter(x=frame.index, y=frame['Active Distance'] / 1000)
#     plt.xlabel('Date')
#     plt.ylabel('Distance / km')
#     plt.title('Active Distance')
#     fig.autofmt_xdate()
#     plt.savefig('/tmp/distance.png')
#
#
# def test_quartiles():
#     # there's a bokeh version of this in the notebooks
#     d = data('-v', '0')
#     stats = d.statistics()
#     print(stats)
#     frame = d.statistic_quartiles('Max Med HR over 30m')
#     print(frame)
#     stats = col_to_boxstats(frame, 'Max Med HR over 30m')
#     print(stats)
#     # https://matplotlib.org/gallery/statistics/bxp.html
#     fig, ax = plt.subplots()
#     ax.bxp(stats, showfliers=False)
#     fig.autofmt_xdate()
#     plt.savefig('/tmp/summary.png')
#
#
# def test_route():
#     d = data('-v', '0')
#     frames = d.activity_waypoints('Bike', '2018-09-06')
#     print(frames)
#     # can't find a good, portable solution past this point
#     # within jupyter, bokeh works ok, but you can't save images without
#     # getting into problems with node (javascript).  seems to be a general
#     # problem of python map libraries.
