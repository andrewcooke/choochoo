
from bokeh.io import output_file, show
from bokeh.plotting import figure
from math import log10
from pandas import DataFrame

from ch2.data import *
from ch2.data.frame import drop_empty
from ch2.data.plot.utils import evenly_spaced_hues
from ch2.data.response2 import sum_to_hour, calc_response, RESPONSE, fit_period, calc_predicted, PREDICTED, \
    calc_measured
from ch2.squeal import *
from ch2.uranus.decorator import template


@template
def fit_ff_many_segments(*segment_names):

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
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')
    hr10 = statistics(s, HR_IMPULSE_10, with_sources=True, constraint=ActivityGroup.from_name(s, 'all'))
    print(hr10.describe())
    segments = [s.query(Segment).filter(Segment.name == segment_name).one() for segment_name in segment_names]
    for segment in segments:
        print(segment, segment.name, segment.distance)
    segment_journals = [s.query(SegmentJournal).filter(SegmentJournal.segment == segment).all()
                        for segment in segments]
    times = [drop_empty(statistics(s, SEGMENT_TIME, sources=segment_journal)).dropna()
             for segment_journal in segment_journals]
    for time in times:
        time.index = time.index.round('1H')
        print(time.describe())
        print(time.columns)
    performances = [DataFrame({segment.name: segment.distance / time[time.columns[0]]}, index=time.index)
                    for segment, time in zip(segments, times)]
    for performance in performances:
        print(performance.describe())

    hr3600 = sum_to_hour(hr10, HR_IMPULSE_10)

    # from pandas import concat
    # single = concat(
    #     [performance.rename(columns={performance.columns[0]: 'Performance'}) for performance in performances],
    #     sort=False)
    # print(single)
    # performances = [single]

    '''
    ## Define Plot Routine
    '''

    output_file(filename='/dev/null')

    def plot(period):
        response = calc_response(hr3600, period)
        f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
        f.line(x=response.index, y=response[RESPONSE], color='grey')
        for color, predicted in zip(evenly_spaced_hues(len(performances)),
                                    calc_predicted(calc_measured(response, performances),
                                                   performances)):
            f.circle(x='Index', y=PREDICTED, source=predicted, color=color)
        show(f)

    '''
    ## Plot Initial Response
    
    Trim and resample data; evaluate and plot our initial model.
    '''

    initial_period = log10(42 * 24)
    plot(initial_period)

    '''
    ## Fit Model
    '''

    result = fit_period(hr3600, initial_period, performances,
                        options={'maxiter': 5})
    print(result)
    period = result.x

    '''
    ### Plot Fitted Response
    '''

    plot(period)
