
from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt

from ch2.command.activity import activity
from ch2.command.constant import constant
from ch2.command.args import bootstrap_file, m, mm, DEV, V, F
from ch2.config.default import default
from ch2.data import data, col_to_boxstats


def import_activity(f):
    bootstrap_file(f, m(V), '0', mm(DEV), configurator=default)
    args, log, db = bootstrap_file(f, m(V), '0', 'constant', '--set', 'FTHR.%', '154')
    constant(args, log)
    args, log, db = bootstrap_file(f, m(V), '0', mm(DEV),
                                   'activity', 'Bike', 'data/test/personal/2018-08-27-rec.fit')
    activity(args, log)


def test_activity():
    with NamedTemporaryFile() as f:
        import_activity(f)
        # there's a bokeh version of this in the notebooks
        d = data(m(V), '0', mm(DEV), m(F), f.name)
        activities = d.activities()
        print(activities)
        statistics = d.statistics()
        print(statistics)
        journals = d.statistic_journals('Active %')
        print(journals)
        # run('sqlite3 %s ".dump"' % f.name, shell=True)


# below assumes data in the local DB

def test_activities():
    d = data()
    frame = d.statistic_journals('Active Distance')
    print(frame)
    fig, ax = plt.subplots()
    plt.scatter(x=frame.index, y=frame['Active Distance'] / 1000)
    plt.xlabel('Date')
    plt.ylabel('Distance / km')
    plt.title('Active Distance')
    fig.autofmt_xdate()
    plt.savefig('/tmp/distance.png')


def test_quartiles():
    # there's a bokeh version of this in the notebooks
    d = data('-v', '0')
    stats = d.statistics()
    print(stats)
    frame = d.statistic_quartiles('Max Med HR over 30m')
    print(frame)
    stats = col_to_boxstats(frame, 'Max Med HR over 30m')
    print(stats)
    # https://matplotlib.org/gallery/statistics/bxp.html
    fig, ax = plt.subplots()
    ax.bxp(stats, showfliers=False)
    fig.autofmt_xdate()
    plt.savefig('/tmp/summary.png')


def test_route():
    d = data('-v', '0')
    frames = d.activity_waypoints('Bike', '2018-09-06')
    print(frames)
    # can't find a good, portable solution past this point
    # within jupyter, bokeh works ok, but you can't save images without
    # getting into problems with node (javascript).  seems to be a general
    # problem of python map libraries.
