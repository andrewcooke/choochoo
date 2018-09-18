
from ch2.data import data


def test_activities():
    ch2 = data('-v', '5')
    cycling = ch2.activity('Cycling')
    stats = cycling.statistics('Active .*')
    for s in stats:
        print(s.name, ':', s.units)
    frame = cycling.activity_statistics(*stats)
    print(frame.describe())
    p = frame.plot.scatter(x='index', y='Active distance')
    # f = figure(plot_width=800, plot_height=250, x_axis_type='datetime', title='Distance for all rides')
    # f.circle(x=frame.index, y=frame['Active distance'] / 1000)
    # f.xaxis.axis_label = 'Date'
    # f.yaxis.axis_label = 'Distance / km'
    # export_png(f, '/tmp/distance.png')


# def test_sumamries():
#     d = data('-v', '5')
#     a = d.activity('Cycling')
#     s = a.summary_statistics('.*')
#     print(s)
