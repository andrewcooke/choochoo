
from bokeh.io import output_file, show
from bokeh.plotting import figure
from math import log10
from pandas import Series

from ch2.data import *
from ch2.data.plot.utils import evenly_spaced_hues
from ch2.data.response import sum_to_hour, calc_response, fit_period, calc_predicted, calc_measured
from ch2.squeal import *
from ch2.uranus.decorator import template


@template
def fit_ff_segments(*segment_names):

    f'''
    # Fit FF Parameters to {', '.join(segment_names)}

    This notebook allows you to estimate a personal time scale (decay period) for the
    [FF model](https://andrewcooke.github.io/choochoo/impulse) using your times (more exactly, the speed)
    on the named segments.

    The resulting value can be used in the configuration so that the Fitness parameter more accurately
    reflects your personal rate of adaption.
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.  We reduce the GR data to hourly values
    so that we have smaller arrays (for faster processing).
    '''

    s = session('-v2')

    hr10 = statistics(s, HR_IMPULSE_10, constraint=ActivityGroup.from_name(s, 'all'))
    print(hr10.describe())
    segments = [s.query(Segment).filter(Segment.name == segment_name).one() for segment_name in segment_names]
    for segment in segments:
        print(segment.name, segment.distance)
    segment_journals = [s.query(SegmentJournal).filter(SegmentJournal.segment == segment).all()
                        for segment in segments]
    times = [drop_empty(statistics(s, SEGMENT_TIME, sources=segment_journal)).dropna()
             for segment_journal in segment_journals]
    for time in times:
        time.index = time.index.round('1H')
    performances = [Series(segment.distance / time.iloc[:, 0], time.index, name=segment.name)
                    for segment, time in zip(segments, times)]
    n_performances = sum(len(performance) for performance in performances)

    hr3600 = sum_to_hour(hr10, HR_IMPULSE_10)

    def copy_of_performances():
        return [performance.copy() for performance in performances]

    '''
    ## Define Plot Routine
    '''

    output_file(filename='/dev/null')

    def plot(period):
        response = calc_response(hr3600, period)
        f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
        f.line(x=response.index, y=response, color='grey')
        for color, predicted in zip(evenly_spaced_hues(len(performances)),
                                    calc_predicted(calc_measured(response, performances),
                                                   performances)):
            f.circle(x=predicted.index, y=predicted, color=color)
        show(f)

    '''
    ## Plot Initial Response
    
    Trim and resample data; evaluate and plot our initial model.
    '''

    initial_period = log10(42 * 24)
    plot(initial_period)

    '''
    ## Fit Model using L1
    
    Adjust tol according to the 'fun' value in the result (tol is the tolerance in that value).
    
    Note how the period (printed, in hours) varies as points are rejected.
    '''

    result = fit_period(hr3600, initial_period, copy_of_performances(),
                        method='L1', reject=n_performances // 10, tol=0.01)
    print(result)
    period = result.x[0]
    print(f'Period in days: {10 ** period / 24:.1f}')
    plot(period)

    '''
    ## Fit Model using L2
    
    Using different methods gives us some idea of how susceptible the value is to processing assumptions.
    For me there was  lot more variation here as points were rejected.
    '''

    result = fit_period(hr3600, initial_period, copy_of_performances(),
                        method='L2', reject=n_performances // 10, tol=0.1)
    print(result)
    period = result.x[0]
    print(f'Period in days: {10 ** period / 24:.1f}')
    plot(period)
