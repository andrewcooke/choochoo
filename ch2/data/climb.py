
from collections import namedtuple
from itertools import groupby
from logging import getLogger

import numpy as np

from .frame import linear_resample, present
from ..lib.data import nearest_index, get_index_loc
from ..squeal import StatisticName, StatisticJournal
from ..stoats.names import _d, ELEVATION, DISTANCE, TOTAL_CLIMB, TIME, CLIMB_ELEVATION, CLIMB_DISTANCE, CLIMB_TIME, \
    CLIMB_GRADIENT

log = getLogger(__name__)

SCORE = 'Score'
GRADIENT = 'Gradient'

# a climb of 80m is roughly equivalent to a score of 8000 on strava's weird approach -
# https://support.strava.com/hc/en-us/articles/216917057-How-are-Strava-climbs-categorized-For-Rides-
MIN_CLIMB_ELEVATION = 80
MIN_CLIMB_GRADIENT = 3
MAX_CLIMB_GRADIENT = 40
MAX_CLIMB_REVERSAL = 0.1

# trade-off between pure elevation (0) and pure gradient (1)
CLIMB_PHI = 0.6

Climb = namedtuple('Climb', 'phi, min_elevation, min_gradient, max_gradient, max_reversal',
                   defaults=(CLIMB_PHI, MIN_CLIMB_ELEVATION, MIN_CLIMB_GRADIENT,
                             MAX_CLIMB_GRADIENT, MAX_CLIMB_REVERSAL))


def find_climbs(df, params=Climb()):
    by_dist = df.set_index(df[DISTANCE])
    by_dist = linear_resample(by_dist, quantise=False)
    for dlo, dhi in find_climb_distances(by_dist, params=params):
        tlo, thi = nearest_index(df, DISTANCE, dlo), nearest_index(df, DISTANCE, dhi)
        log.debug(f'Found climb from {tlo} - {thi} ({dlo}m - {dhi}m)')
        up = df[ELEVATION].loc[thi] - df[ELEVATION].loc[tlo]
        along = df[DISTANCE].loc[thi] - df[DISTANCE].loc[tlo]
        yield {TIME: thi, CLIMB_ELEVATION: up, CLIMB_DISTANCE: along,
               CLIMB_TIME: (thi - tlo).total_seconds(), CLIMB_GRADIENT: 100 * up / along}


def find_climb_distances(df, params=Climb()):
    mn, mx = df[ELEVATION].min(), df[ELEVATION].max()
    if mx - mn > params.min_elevation:
        score, lo, hi = biggest_climb(df, params=params)
        if score:
            a, b, c = split(df, lo, hi)
            yield from find_climb_distances(a, params=params)
            yield from contiguous(b, params=params)
            yield from find_climb_distances(c, params=params)


def split(df, lo, hi, inside=True):
    ilo, ihi = get_index_loc(df, lo), get_index_loc(df, hi)
    if ilo > ihi:
        ilo, ihi = ihi, ilo
    if inside:
        ihi += 1
    else:
        ilo += 1
    return df.iloc[:ilo].copy(), df.iloc[ilo:ihi].copy(), df.iloc[ihi:].copy()


def contiguous(df, params=Climb()):
    up = df[ELEVATION].iloc[-1] - df[ELEVATION].iloc[0]
    if up >= params.min_elevation:
        down, lo, hi = biggest_reversal(df)
        if down and down > params.max_reversal * up:
            a, b, c = split(df, lo, hi, inside=False)
            yield from contiguous(a, params=params)
            yield from find_climb_distances(b, params=params)
            yield from contiguous(c, params=params)
        else:
            along = df.index[-1] - df.index[0]
            if along and 100 * up / along < params.max_gradient:
                yield df.index[0], df.index[-1]


def first_or_none(generator):
    try:
        return next(generator)
    except StopIteration:
        return None


def biggest_reversal(df):
    max_elevation, max_indices, d = 0, (None, None), df.index[1] - df.index[0]
    for offset in range(1, len(df)-1):
        df[_d(ELEVATION)] = df[ELEVATION].diff(-offset)
        if present(df, _d(ELEVATION)):
            d_elevation = df[_d(ELEVATION)].dropna().max()
            if d_elevation > max_elevation:
                max_elevation = d_elevation
                hi = df.loc[df[_d(ELEVATION)] == max_elevation].index[0]  # break ties
                lo = df.index[get_index_loc(df, hi) + offset]
                max_indices = (lo, hi)
    return max_elevation, max_indices[0], max_indices[1]


def biggest_climb(df, params=Climb(), grid=10):
    # returns (score, dlo, dhi))
    # use distances (indices) rather than ilocs because we're subdividing the data
    if len(df) > 100 * grid:
        score, lo, hi = search(df.iloc[::grid].copy())
        if score:
            # need to pass through iloc to extend range
            ilo, ihi = get_index_loc(df, lo), get_index_loc(df, hi)
            return search(df.iloc[max(0, ilo-grid):min(ihi+grid, len(df)-1)].copy(), params=params)
        else:
            return 0, None, None
    else:
        return search(df, params=params)


def search(df, params=Climb()):
    # returns (score, dlo, dhi)
    # use times (indices) rather than ilocs because we're subdividing the data
    max_score, max_indices, d = 0, (None, None), df.index[1] - df.index[0]
    for offset in range(len(df)-1, 0, -1):
        df[_d(ELEVATION)] = df[ELEVATION].diff(offset)
        d_distance = d * offset
        min_elevation = max(params.min_elevation, params.min_gradient * d_distance / 100)
        if df[_d(ELEVATION)].max() > min_elevation:  # avoid some work
            df[SCORE] = df[_d(ELEVATION)] / d_distance ** params.phi
            score = df.loc[df[_d(ELEVATION)] > min_elevation, SCORE].max()
            if not np.isnan(score) and score > max_score:
                max_score = score
                hi = df.loc[df[SCORE] == max_score].index[0]  # arbitrarily pick one if tied (error here w item())
                lo = df.index[get_index_loc(df, hi) - offset]
                max_indices = (lo, hi)
    return max_score, max_indices[0], max_indices[1]


def climbs_for_activity(s, ajournal):

    from ..stoats.calculate.activity import ActivityCalculator

    total = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticName.name == TOTAL_CLIMB,
               StatisticJournal.time == ajournal.start,
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group).order_by(StatisticJournal.time).one_or_none()
    statistics = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticName.name.like('Climb %'),
               StatisticJournal.time >= ajournal.start,
               StatisticJournal.time <= ajournal.finish,
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group).order_by(StatisticJournal.time).all()
    return total, sorted((dict((statistic.statistic_name.name, statistic) for statistic in climb_statistics)
                          for _, climb_statistics in groupby(statistics, key=lambda statistic: statistic.time)),
                         key=lambda climb: climb[CLIMB_ELEVATION].value, reverse=True)


# if __name__ == '__main__':
#     from ch2.data import *
#     start = time()
#     date = '2017-05-28 10:28:13'  # 1495103293
#     s = session('-v5')
#     df = activity_statistics(s, DISTANCE, ELEVATION, local_time=date, activity_group_name='Bike', with_timespan=False)
#     print(list(find_climbs(df)))
#     print(time() - start)

    # prev
    # Sunday, 28 May 2017 15:26:17
    # Sunday, 28 May 2017 16:03:51
    # Sunday, 28 May 2017 16:47:57
    # Sunday, 28 May 2017 17:19:28
    # Sunday, 28 May 2017 17:38:05

    # this
    # (Timestamp('2017-05-28 15:15:55+0000', tz='UTC'), Timestamp('2017-05-28 15:26:17+0000', tz='UTC'))
    # (Timestamp('2017-05-28 15:31:01+0000', tz='UTC'), Timestamp('2017-05-28 16:03:51+0000', tz='UTC'))
    # (Timestamp('2017-05-28 16:04:23+0000', tz='UTC'), Timestamp('2017-05-28 16:47:57+0000', tz='UTC'))
    # (Timestamp('2017-05-28 17:03:44+0000', tz='UTC'), Timestamp('2017-05-28 17:42:38+0000', tz='UTC'))
