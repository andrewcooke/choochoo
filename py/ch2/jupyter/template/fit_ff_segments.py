
from bokeh.io import output_file, show
from bokeh.plotting import figure
from math import log10

from ch2.data import *
from ch2.data.plot.utils import evenly_spaced_hues
from ch2.data.response import *
from ch2.jupyter.decorator import template
from ch2.lib.utils import group_to_dict
from ch2.pipeline.owners import *
from ch2.sql import *


@template
def fit_ff_segments(group, *segment_titles):

    f'''
    # Fit FF Parameters for {group} to {', '.join(segment_titles)}

    This notebook allows you to estimate a personal time scale (decay period) for the
    [FF model](https://andrewcooke.github.io/choochoo/impulse) using your times (more exactly, the speed)
    on the named segments.

    The resulting value can be used in the configuration so that the Fitness parameter more accurately
    reflects your personal rate of adaption.

    For more information see the [documentation](https://andrewcooke.github.io/choochoo/ff-fitting).
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

    # hr10 = statistics(s, HR_IMPULSE_10, activity_group=ActivityGroup.from_name(s, 'all'))
    hr10 = Statistics(s).by_name(MonitorReader, N.HR_IMPULSE_10).df
    print(hr10.describe())
    segments = [s.query(Segment).filter(Segment.title == segment_title).one() for segment_title in segment_titles]
    for segment in segments:
        print(segment.title, segment.distance)
    kit_statistic = StatisticName.from_name(s, ActivityReader.KIT, ActivityReader)
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
            if len(times.columns) and len(times.index) > 2:
                times.index = times.index.round('1H')
                performances.append(Series(segment.distance / times.iloc[:, 0], times.index,
                                           name=f'{segment.title}/{kit}'))
    n_performances = sum(len(performance) for performance in performances)

    hr3600 = sum_to_hour(hr10, HR_IMPULSE_10)

    def copy_of_performances():
        return [performance.copy() for performance in performances]

    for performance in performances:
        print(performance)

    '''
    ## Define Plot Routine

    Below the `params` are (currently) log10_period and log10_start - the time period for decay and the initial
    response (fitness) value.  We use log10 so that the values cannot be negative.
    '''

    output_file(filename='/dev/null')

    def plot_params(params, rejected=tuple()):
        response = calc_response(hr3600, params)
        predicted = calc_observed(restrict_response(response, performances), performances)
        f = figure(title=fmt_params(params), plot_width=500, plot_height=450, x_axis_type='datetime')
        f.line(x=response.index, y=response, color='grey')
        for color, prediction, performance in zip(evenly_spaced_hues(len(performances)), predicted, performances):
            f.circle(x=prediction.index, y=prediction, color=color, legend_label=performance.name)
        for i, t in rejected:
            f.x(x=t, y=predicted[i].loc[t], color='black', size=10)
        f.legend.location = 'bottom_left'
        show(f)

    '''
    ## Plot Initial Response
    
    Trim and resample data; evaluate and plot our initial model.
    '''

    initial_period = log10(42 * 24)
    plot_params((initial_period,))

    '''
    ## Explore Effect of Start
    '''
    plot_params((initial_period, log10(1000)))
    plot_params((initial_period, log10(3000)))

    '''
    ## Fit Model using L1
    
    Adjust tol according to the 'fun' value in the result (tol is the tolerance in that value).
    
    Note how the period (printed, in hours) varies as points are rejected.
    '''

    result, rejected = fit_ff_params(hr3600, (initial_period,), copy_of_performances(),
                                     method='L1', tol=0.01,
                                     max_reject=n_performances // 2, threshold=(2, 0.2))
    print(result)
    plot_params(result.x, rejected=rejected)

    result, rejected = fit_ff_params(hr3600, (initial_period, 0), copy_of_performances(),
                                     method='L1', tol=0.01,
                                     max_reject=n_performances // 2, threshold=(2, 0.2))
    print(result)
    plot_params(result.x, rejected=rejected)

    '''
    ## Fit Model using L2
    
    Using different methods gives us some idea of how susceptible the value is to processing assumptions.
    
    Note that the thresholds change for the L2 norm.
    '''

    initial_period = log10(42 * 24)
    result, rejected = fit_ff_params(hr3600, (initial_period,), copy_of_performances(),
                                     method='L2', tol=0.01,
                                     max_reject=n_performances // 2, threshold=(500, 50))
    print(result)
    plot_params(result.x, rejected=rejected)

    result, rejected = fit_ff_params(hr3600, (initial_period, 0), copy_of_performances(),
                                     method='L2', tol=0.01,
                                     max_reject=n_performances // 2, threshold=(500, 50))
    print(result)
    plot_params(result.x, rejected=rejected)
