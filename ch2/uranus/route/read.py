
import numpy as np
import pandas as pd

from ...data.frame import set_log
from ...data import activity_statistics, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, \
    ELEVATION, SPEED, CADENCE, TIMESPAN_ID, TIME, POW_TWO


def d(name): return f'Delta {name}'


def avg(name): return f'Avg {name}'

ENERGY = 'Energy'
SPEED_2 = f'{SPEED}{POW_TWO}'
AVG_SPEED_2 = avg(SPEED_2)
DELTA_SPEED_2 = d(SPEED_2)
DELTA_TIME = d(TIME)
DELTA_DISTANCE = d(DISTANCE)
DELTA_ELEVATION = d(ELEVATION)
DELTA_SPEED = d(SPEED)
DELTA_ENERGY = d(ENERGY)
CDA = 'CdA'
CRR = 'Crr'


def std_route(s, step='10s', bookmarks=None, local_time=None, time=None, activity_journal_id=None,
              activity_group_name=None, activity_group_id=None, log=None):

    set_log(log)
    stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE,
                                ELEVATION, SPEED, CADENCE,
                                bookmarks=bookmarks, local_time=local_time, time=time,
                                activity_journal_id=activity_journal_id, activity_group_name=activity_group_name,
                                activity_group_id=activity_group_id, with_timespan=True)
    stats[SPEED_2] = stats[SPEED] ** 2
    stats = pd.concat(_diff(stats, step))
    return stats


def _diff(stats, step):
    for _, span in stats.groupby(TIMESPAN_ID):
        span = span.resample(step).mean().interpolate(method='spline', order=3)
        span[TIME] = span.index
        for col in TIME, DISTANCE, ELEVATION, SPEED, SPEED_2:
            span[d(col)] = span[col].diff()
        avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(span[SPEED], span[SPEED][1:])]
        span[AVG_SPEED_2] = [np.nan] + avg_speed_2
        yield span


def add_energy_budget(route, m, g=9.8):
    route[DELTA_ENERGY] = m * (route[DELTA_SPEED_2] / 2 + route[DELTA_ELEVATION] * g)


def add_cda_estimate(route, p=1.225):
    route[CDA] = -route[DELTA_ENERGY] / (p * route[AVG_SPEED_2] * route[DELTA_DISTANCE] * 0.5)


def add_crr_estimate(route):
    route[CRR] = -route[DELTA_ENERGY] / route[DELTA_DISTANCE]
