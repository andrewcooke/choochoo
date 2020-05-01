
import numpy as np
from bokeh.io import show, output_file
from bokeh.plotting import figure

from ch2.data import *
from ch2.read.monitor import MonitorReader
from ch2.jupyter.decorator import template


@template
def heart_rate(start, finish):

    f'''
    # Heart Rate: {start} - {finish}
    '''

    '''
    Extract and prepare data.
    '''

    bin_width = 1

    s = session('-v2')
    df = statistics(s, HEART_RATE, owner=MonitorReader, local_start=start, local_finish=finish)
    data = sorted(df[HEART_RATE])
    # take care here to get a fixed number of (integer) heart rates in each bin
    # this avoids aliasing effects.
    lo, hi = data[0] - 0.5, data[-1] + 0.5
    n = int(hi - lo + bin_width - 0.5) // bin_width
    hi = lo + n * bin_width
    hist, edges = np.histogram(data, density=True, bins=n, range=(lo, hi))
    y_max = max(hist)

    '''
    Plot histogram of heart rate and mark percentiles used to calculate rest value.
    
    The percentiles used are taken from the MonitorCalculator source (currently they are not configurable).
    It's not clear to me what the 'correct' values should be, but 10% seems to be reasonable, discarding possibly
    erroneous low counts but still giving a value from the bottom end of the range.
    '''

    output_file(filename='/dev/null')

    f = figure(title=f'Heart Rate: {start} - {finish}')
    f.xaxis.axis_label = 'Heart Rate / bpm'
    f.yaxis.axis_label = 'Measurement Density'
    f.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="grey", line_color="white", alpha=0.5)
    for pc in (5, 10, 15):
        x = data[int(len(data) * pc / 100)]
        f.line([x, x], [0, y_max], line_color='red', line_dash='dashed')
    show(f)
