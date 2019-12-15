
from bokeh.io import output_notebook, show
from math import pi, sin, cos

from ch2.data import *
from ch2.data.plot import *
from ch2.jupyter.decorator import template
from ch2.sql import *


@template
def nearby_activities(constraint):

    f'''
    # Nearby Activities: {constraint}
    '''

    '''
    $contents
    '''

    '''
    ## Load Group
    '''
    s = session('-v2')
    groups = df(s.query(ActivityNearby).filter(ActivityNearby.constraint == constraint))
    n_groups = len(groups.constraint.unique())

    '''
    ## Load and Plot Route Data
    '''

    offset_a, offset_b = 400, 150
    x_max, y_max = None, None
    # you can provide manual labels here
    labels = None
    palette = list(evenly_spaced_hues(n_groups, saturation=0.8, value=0.8))

    output_notebook()
    f = figure(plot_width=900, plot_height=900, x_axis_type='mercator', y_axis_type='mercator')
    f.add_tile(STAMEN_TERRAIN, alpha=0.5)

    for i in range(n_groups):
        source_ids = groups.loc[groups.constraint == i].activity_journal_id
        n_source_ids = len(source_ids)
        a = 2 * pi * i / n_groups
        dxa, dya = offset_a * sin(a), offset_a * cos(a)
        for j, source_id in enumerate(source_ids):
            b = 2 * pi * j / n_source_ids
            dxb, dyb = offset_b * sin(b), offset_b * cos(b)
            df = activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                     activity_journal=ActivityJournal.from_id(s, source_id))
            f.line(x=df[SPHERICAL_MERCATOR_X] + dxa + dxb, y=df[SPHERICAL_MERCATOR_Y] + dya + dyb,
                   color=palette[i], line_width=1.5, line_dash='dotted')
            if x_max is None:
                x_max, y_max = max(df[SPHERICAL_MERCATOR_X]), max(df[SPHERICAL_MERCATOR_Y])
            else:
                x_max, y_max = max(x_max, max(df[SPHERICAL_MERCATOR_X])), max(y_max, max(df[SPHERICAL_MERCATOR_Y]))

    if not labels:
        labels = [f'{constraint} {g}' for g in range(n_groups)]
    for i in range(n_groups):
        source_ids = groups.loc[groups.constraint == i].activity_journal_id
        n_source_ids = len(source_ids)
        f.line(x=[x_max, x_max * 1.001], y=[y_max, y_max], color=palette[i], line_width=5, line_dash='solid',
               legend_label='%s (%d)' % (labels[i], n_source_ids))

    f.xaxis.axis_label = 'Longitude'
    f.yaxis.axis_label = 'Latitude'
    show(f)
