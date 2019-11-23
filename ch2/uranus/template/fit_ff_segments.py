
from bokeh.io import output_file, show
from bokeh.plotting import figure
from math import log10
from pandas import Series

from ch2.data import *
from ch2.data.plot.utils import evenly_spaced_hues
from ch2.data.response import sum_to_hour, calc_response, fit_period, calc_predicted, calc_measured
from ch2.lib import groupby_tuple
from ch2.lib.utils import group_to_dict
from ch2.squeal import *
from ch2.stoats.read.segment import SegmentReader
from ch2.uranus.decorator import template


@template
def fit_ff_segments(group, *segment_names):

    f'''
    # Fit FF Parameters for {group} to {', '.join(segment_names)}

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
    We reduce the HR data to hourly values so that we have smaller arrays (for faster processing).
    '''

    s = session('-v2')

    hr10 = statistics(s, HR_IMPULSE_10, constraint=ActivityGroup.from_name(s, 'all'))
    print(hr10.describe())
    segments = [s.query(Segment).filter(Segment.name == segment_name).one() for segment_name in segment_names]
    for segment in segments:
        print(segment.name, segment.distance)
    kit_statistic = StatisticName.from_name(s, 'kit', SegmentReader, ActivityGroup.from_name(s, group))
    journals_by_kit_by_segment = \
        {segment: group_to_dict(s.query(StatisticJournalText.value, SegmentJournal).
                                join(ActivityJournal, SegmentJournal.activity_journal_id == ActivityJournal.id).
                                join(StatisticJournalText, StatisticJournalText.source_id == ActivityJournal.id).
                                filter(StatisticJournalText.statistic_name_id == kit_statistic.id,
                                       SegmentJournal.segment == segment).all())
         for segment in segments}
    times_by_kit_by_segment = \
        {segment: {kit: drop_empty(statistics(s, SEGMENT_TIME, sources=journals)).dropna()
                   for kit, journals in journals_by_kit_by_segment[segment].items()}
         for segment in segments}
    performances = []
    for segment in segments:
        for kit, times in times_by_kit_by_segment[segment].items():
            times.index = times.index.round('1H')
            performances.append(Series(segment.distance / times.iloc[:, 0], times.index,
                                       name=f'{segment.name}/{kit}'))
    n_performances = sum(len(performance) for performance in performances)

    hr3600 = sum_to_hour(hr10, HR_IMPULSE_10)

    def copy_of_performances():
        return [performance.copy() for performance in performances]

    for performance in performances:
        print(performance)

    '''
    ## Define Plot Routine
    '''

    output_file(filename='/dev/null')

    def plot(period):
        response = calc_response(hr3600, period)
        f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
        f.line(x=response.index, y=response, color='grey')
        for color, predicted, performance in zip(evenly_spaced_hues(len(performances)),
                                                 calc_predicted(calc_measured(response, performances), performances),
                                                 performances):
            f.circle(x=predicted.index, y=predicted, color=color, legend_label=performance.name)
        f.legend.location = 'bottom_left'
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
