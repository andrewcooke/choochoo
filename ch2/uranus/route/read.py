
import pandas as pd

from ...data.frame import set_log
from ...data import activity_statistics, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, \
    ELEVATION, SPEED, CADENCE, TIMESPAN_ID, TIME


def d(name):
    return f'delta {name}'


def std_route(s, step='10s', local_time=None, time=None, group=None, activity_journal_id=None, log=None):

    set_log(log)
    stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE,
                                ELEVATION, SPEED, CADENCE,
                                local_time=local_time, time=time, group=group,
                                activity_journal_id=activity_journal_id, with_timespan=True)
    stats[TIME] = stats.index
    stats = pd.concat(_diff(stats, step))
    return stats


def _diff(stats, step):
    for _, span in stats.groupby(TIMESPAN_ID):
        span = span.resample(step).mean().interpolate(method='spline', order=3)
        for col in TIME, DISTANCE, ELEVATION, SPEED:
            span[d(col)] = span[col].diff()
        span = span.iloc[1:]
        yield span
