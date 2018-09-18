
import matplotlib.pyplot as plt

from ch2.data import data, col_to_boxstats


def test_activities():
    # there's a bokeh version of this in the notebooks
    ch2 = data('-v', '5')
    cycling = ch2.activity('Cycling')
    stats = cycling.statistics('Active .*')
    for s in stats:
        print(s.name, ':', s.units)
    frame = cycling.activity_statistics(*stats)
    print(frame.describe())
    plt.scatter(x=frame.index, y=frame['Active distance'] / 1000)
    plt.xlabel('Date')
    plt.ylabel('Distance / km')
    plt.title('Active distance')
    plt.savefig('/tmp/distance.png')


def test_sumamries():
    # there's a bokeh version of this in the notebooks
    ch2 = data('-v', '0')
    cycling = ch2.activity('Cycling')
    stats = cycling.statistics('.*')
    for s in stats:
        print(s.name, ':', s.units)
    frame = cycling.summary_statistics('Max med HR over 30m')
    stats = col_to_boxstats(frame, 'Max med HR over 30m')
    # https://matplotlib.org/gallery/statistics/bxp.html
    fig, ax = plt.subplots()
    ax.bxp(stats, showfliers=False)
    fig.autofmt_xdate()
    plt.savefig('/tmp/summary.png')


def test_route():
    ch2 = data('-v', '0')
    cycling = ch2.activity('Cycling')
    frames = cycling.activity_diary('2018-09-06-rec')
    # can't find a good, portable solution past this point
    # within jupyter, bokeh works ok, but you can't save images without
    # getting into problems with node (javascript).  seems to be a general
    # problem of python map libraries.
