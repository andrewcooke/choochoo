
import numpy as np
from bokeh.io import show, output_file
from bokeh.plotting import figure

from ch2.data import *
from ch2.stoats.read.monitor import MonitorReader
from ch2.uranus.decorator import template


@template
def heart_rate(start, finish):

    f'''
    # Heart Rate: {start.split()[0]} - {finish.split()[0]}
    '''

    '''
    Extract and prepare data.
    '''

    bin_width = 1

    s = session('-v2')
    df = statistics(s, HEART_RATE, owner=MonitorReader, start=start, finish=finish)
    data = sorted(df[HEART_RATE])
    lo, hi = data[0] - 0.5, data[-1] + 0.5
    n = int(hi - lo + bin_width - 0.5) // bin_width
    hi = lo + n * bin_width
    hist, edges = np.histogram(data, density=True, bins=n, range=(lo, hi))
    y_max = max(hist)

    '''
    Plot histogram of heart rate and mark percentiles used to calculate rest value.
    '''

    output_file(filename='/dev/null')

    f = figure()
    f.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="grey", line_color="white", alpha=0.5)
    for pc in (5, 10, 15):
        x = data[int(len(data) * pc / 100)]
        f.line([x, x], [0, y_max], line_color='red', line_dash='dashed')
    show(f)
