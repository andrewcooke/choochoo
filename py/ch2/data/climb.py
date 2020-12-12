from collections import namedtuple
from functools import cmp_to_key
from itertools import groupby
from logging import getLogger

from sqlalchemy import or_

from .frame import linear_resample, present
from ..common.math import is_nan
from ..lib.data import nearest_index, get_index_loc, safe_yield
from ..names import Names as N
from ..sql import StatisticName, StatisticJournal, Source, ActivityJournal
from ..sql.tables.sector import SectorJournal

log = getLogger(__name__)

SCORE = 'Score'
GRADIENT = 'Gradient'

# a climb of 80m is roughly equivalent to a score of 8000 on strava's weird approach -
# https://support.strava.com/hc/en-us/articles/216917057-How-are-Strava-climbs-categorized-For-Rides-
MIN_CLIMB_ELEVATION = 80
MIN_CLIMB_GRADIENT = 3
MAX_CLIMB_GRADIENT = 40
MAX_CLIMB_REVERSAL = 0.1
CLIMB_CATEGORIES = {MIN_CLIMB_ELEVATION: '4', 160: '3', 320: '2', 640: '1', 800: 'HC'}

# conversion of gradient to percent, but correcting for distance in km
PERCENT = 100 / 1000

# trade-off between pure elevation (0) and pure gradient (1)
CLIMB_PHI = 0.7

Climb = namedtuple('Climb', 'phi, min_elevation, min_gradient, max_gradient, max_reversal',
                   defaults=(CLIMB_PHI, MIN_CLIMB_ELEVATION, MIN_CLIMB_GRADIENT,
                             MAX_CLIMB_GRADIENT, MAX_CLIMB_REVERSAL))


@safe_yield
def find_climbs(df, params=Climb()):
    df = df.drop_duplicates(subset=[N.DISTANCE])
    by_dist = df.set_index(df[N.DISTANCE])
    by_dist = linear_resample(by_dist, quantise=False)
    for dlo, dhi in find_climb_distances(by_dist, params=params):
        tlo, thi = nearest_index(df, N.DISTANCE, dlo), nearest_index(df, N.DISTANCE, dhi)
        log.debug(f'Found climb from {tlo} - {thi} ({dlo}km - {dhi}km)')
        up = df[N.ELEVATION].loc[thi] - df[N.ELEVATION].loc[tlo]
        along = df[N.DISTANCE].loc[thi] - df[N.DISTANCE].loc[tlo]
        climb = {N.TIME: thi,
                 N.CLIMB_ELEVATION: up,
                 N.CLIMB_DISTANCE: along,
                 N.CLIMB_TIME: (thi - tlo).total_seconds(),
                 N.CLIMB_GRADIENT: PERCENT * up / along}
        for height in sorted(CLIMB_CATEGORIES.keys()):
            if up >= height:
                climb[N.CLIMB_CATEGORY] = CLIMB_CATEGORIES[height]
            else:
                break
        log.debug(climb)
        yield climb


def find_climb_distances(df, params=Climb()):
    mn, mx = df[N.ELEVATION].min(), df[N.ELEVATION].max()
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
    up = df[N.ELEVATION].iloc[-1] - df[N.ELEVATION].iloc[0]
    if up >= params.min_elevation:
        down, lo, hi = biggest_reversal(df)
        if down and down > params.max_reversal * up:
            a, b, c = split(df, lo, hi, inside=False)
            yield from contiguous(a, params=params)
            yield from find_climb_distances(b, params=params)
            yield from contiguous(c, params=params)
        else:
            along = df.index[-1] - df.index[0]
            if along and PERCENT * up / along < params.max_gradient:
                yield df.index[0], df.index[-1]


def first_or_none(generator):
    try:
        return next(generator)
    except StopIteration:
        return None


def biggest_reversal(df):
    max_elevation, max_indices, d = 0, (None, None), df.index[1] - df.index[0]
    for offset in range(1, len(df)-1):
        df[N._delta(N.ELEVATION)] = df[N.ELEVATION].diff(-offset)
        if present(df, N._delta(N.ELEVATION)):
            d_elevation = df[N._delta(N.ELEVATION)].dropna().max()
            if d_elevation > max_elevation:
                max_elevation = d_elevation
                hi = df.loc[df[N._delta(N.ELEVATION)] == max_elevation].index[0]  # break ties
                lo = df.index[get_index_loc(df, hi) + offset]
                max_indices = (lo, hi)
    return max_elevation, max_indices[0], max_indices[1]


def biggest_climb(df, params=Climb(), grid=10):
    # returns (score, dlo, dhi))
    # use distances (indices) rather than ilocs because we're subdividing the data
    if len(df) > 100 * grid:
        score, lo, hi = search(df.iloc[::grid].copy(), grid=True)
        if score:
            # need to pass through iloc to extend range
            ilo, ihi = get_index_loc(df, lo), get_index_loc(df, hi)
            return search(df.iloc[max(0, ilo-grid):min(ihi+grid, len(df)-1)].copy(), params=params)
        else:
            return 0, None, None
    else:
        return search(df, params=params)


def search(df, params=Climb(), grid=False):
    # returns (score, dlo, dhi)
    # use distance (indices) rather than ilocs because we're subdividing the data
    max_score, max_indices, d = 0, (None, None), df.index[1] - df.index[0]
    for offset in range(len(df)-1, 0, -1):
        df[N._delta(N.ELEVATION)] = df[N.ELEVATION].diff(offset)
        d_distance = d * offset
        min_elevation = max(params.min_elevation, params.min_gradient * d_distance / PERCENT)
        if df[N._delta(N.ELEVATION)].max() > min_elevation:  # avoid some work
            # factor of 1000 below to convert km to m
            df[SCORE] = df[N._delta(N.ELEVATION)] / ((1000 * d_distance) ** params.phi)
            score = df.loc[df[N._delta(N.ELEVATION)] > min_elevation, SCORE].max()
            if not is_nan(score) and score > max_score:
                max_score = score
                hi = df.loc[df[SCORE] == max_score].index[0]  # arbitrarily pick one if tied (error here w item())
                lo = df.index[get_index_loc(df, hi) - offset]
                if not grid:
                    # step inwards one location from each end
                    # (so that we have some 'extra' to aid with intersections)
                    lo = df.index[get_index_loc(df, hi) - (offset-1)]
                    hi = df.index[get_index_loc(df, hi) - 1]
                max_indices = (lo, hi)
    return max_score, max_indices[0], max_indices[1]


def climbs_for_activity(s, ajournal):

    from ..pipeline.calculate.sector import SectorCalculator
    from ..pipeline.calculate import ActivityCalculator

    total = s.query(StatisticJournal). \
        join(StatisticName, Source). \
        filter(StatisticName.name == N.TOTAL_CLIMB,
               StatisticJournal.time == ajournal.start,
               StatisticName.owner == ActivityCalculator,
               Source.activity_group == ajournal.activity_group).order_by(StatisticJournal.time).one_or_none()
    query = s.query(StatisticJournal). \
        join(StatisticName, Source). \
        join(SectorJournal, SectorJournal.id == Source.id). \
        filter(or_(StatisticName.name.like(N.CLIMB_ANY),
                   StatisticName.name == N.VERTICAL_POWER),
               StatisticJournal.time >= ajournal.start,
               StatisticJournal.time <= ajournal.finish,
               StatisticName.owner == SectorCalculator,
               Source.activity_group == ajournal.activity_group).order_by(StatisticJournal.time)
    sjournals = query.all()

    def make_climb(sjournals):
        sjournals = list(sjournals)
        climb = {sjournal.statistic_name.name: sjournal for sjournal in sjournals}
        climb['start-distance'] = sjournals[0].source.start_distance
        climb['sector-journal-id'] = sjournals[0].source.id
        climb['sector-id'] = sjournals[0].source.sector_id
        return climb

    def cmp_climb(a, b):
        # if start distances are similar, order by elevation
        if abs(a['start-distance'] - b['start-distance']) / (a['start-distance'] + b['start-distance']) > 0.03:
            return a['start-distance'] - b['start-distance']
        else:
            return a[N.CLIMB_ELEVATION].value - b[N.CLIMB_ELEVATION].value

    return total, sorted((make_climb(grouped)
                          for _, grouped in groupby(sjournals, key=lambda sjournal: sjournal.time)),
                         key=cmp_to_key(cmp_climb))


def climb_sources(s, activity_journal, activity_group=None):
    if not isinstance(activity_journal, Source):
        activity_journal = ActivityJournal.at(s, activity_journal, activity_group=activity_group)
    return s.query(SectorJournal).filter(SectorJournal.activity_journal_id == activity_journal.id).all()
