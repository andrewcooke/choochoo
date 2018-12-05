
import datetime as dt

from bokeh.io import show, output_notebook
from bokeh.layouts import column
from bokeh.models.widgets import Dropdown
from bokeh.plotting import figure


def col_to_boxstats(frame, name):
    '''
    Allow inter-op with matplotlib using pre-calculated stats
    See test_data.py
    '''
    stats = []
    for index, row in frame.iterrows():
        if row[name]:
            stats.append({'label': index,
                          'whislo': row[name][0],
                          'q1': row[name][1],
                          'med': row[name][2],
                          'q3': row[name][3],
                          'whishi': row[name][4]})
    return stats


def bokeh_boxplot(f, col):
    '''
    Generate a boxplot for a column (pandas series) containing a tuple of 5 values
    (index date) as provided by summary statistics,
    '''
    def pick(n):
        def pick(x):
            return x[n] if x else None
        return pick
    q = [col.map(pick(i)) for i in range(5)]
    f.segment(q[0].index, q[0], q[1].index, q[1])
    f.vbar(q[1].index, dt.timedelta(days=20), q[1], q[2], fill_alpha=0)
    f.vbar(q[2].index, dt.timedelta(days=20), q[2], q[3], fill_alpha=0)
    f.segment(q[3].index, q[3], q[4].index, q[4])


def statistic_gui(data):

    statistics = data.statistic_names()
    output_notebook()

    def modify_doc(doc):

        f = figure(plot_width=800, plot_height=400)
        f.xaxis.axis_label = 'Date'
        m = Dropdown(label='Statistic',
                     menu=list(zip(statistics['name'].tolist(), (str(i) for i in statistics.index.tolist()))))
        r = column(m, f)

        def mkplot(index):
            f = figure(plot_width=500, plot_height=500)
            f.xaxis.axis_label = 'Date'
            r.children[1] = f
            row = statistics.iloc[int(index)]
            name = row['name']
            d = data.statistic_journals(name, constraint=row['constraint'], owner=row['owner'])
            f.circle(d.index, d[name], line_width=2, legend=name)
            f.legend.location = 'top_left'

        m.on_change('value', lambda attr, old, new: mkplot(new))
        doc.add_root(r)

    show(modify_doc)
