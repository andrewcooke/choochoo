
from collections import defaultdict, namedtuple
from itertools import groupby
from logging import getLogger
from random import uniform

from sqlalchemy import inspect, select, alias, and_, distinct, func, not_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import count

from .utils import ProcessCalculator
from ..pipeline import OwnerInMixin
from ...common.log import log_current_exception
from ...lib.dbscan import DBSCAN
from ...lib.optimizn import expand_max
from ...names import Names
from ...rtree import MatchType
from ...rtree.spherical import SQRTree
from ...sql import ActivityJournal, ActivityGroup, ActivitySimilarity, ActivityNearby, StatisticName, \
    StatisticJournal, StatisticJournalFloat, Timestamp

log = getLogger(__name__)
Nearby = namedtuple('Nearby', 'constraint, activity_group, border, start, finish, '
                              'latitude, longitude, height, width, fraction')


class SimilarityCalculator(OwnerInMixin, ProcessCalculator):

    def __init__(self, *args, fraction=0.01, border=150, **kargs):
        self.fraction = fraction
        self.border = border
        super().__init__(*args, **kargs)

    def _startup(self, s):
        log.info(f'Reducing to {int(0.5 + 100 * self.fraction):d}%')

    def _missing(self, s):
        prev = Timestamp.get(s, self.owner_out)
        if not prev:
            return [True]
        prev_ids = s.query(Timestamp.source_id). \
            filter(Timestamp.owner == self.owner_in,
                   Timestamp.constraint == None,
                   Timestamp.time < prev.time).cte()
        later = s.query(count(ActivityJournal.id)). \
            join(ActivityGroup). \
            filter(not_(ActivityJournal.id.in_(prev_ids))).scalar()
        if later:
            return [True]
        else:
            return []

    def _delete(self, s):
        log.warning(f'Deleting similarity data')
        s.query(ActivitySimilarity).delete(synchronize_session=False)
        Timestamp.clear(s, self.owner_out)
        s.commit()

    def _run_one(self, s, missed):
        rtree = SQRTree(default_match=MatchType.OVERLAP, default_border=self.border)
        n_points = defaultdict(lambda: 0)
        self._prepare(s, rtree, n_points, 30000)
        n_overlaps = defaultdict(lambda: defaultdict(lambda: 0))
        new_ids, affected_ids = self._count_overlaps(s, rtree, n_points, n_overlaps, 10000)
        # this clears itself beforehand
        # use explicit class to distinguish from subclasses (which compare against this)
        with Timestamp(owner=self.owner_out).on_success(s):
            self._save(s, new_ids, affected_ids, n_points, n_overlaps, 10000)

    def _prepare(self, s, rtree, n_points, delta):
        n = 0
        for aj_id_in, lon, lat in self._filter(self._aj_lon_lat(s, new=False)):
            posn = [(lon, lat)]
            rtree[posn] = aj_id_in
            n_points[aj_id_in] += 1
            n += 1
            if n % delta == 0:
                log.info(f'Loaded {n} points')
        if n % delta:
            log.info(f'Loaded {n} points')

    def _count_overlaps(self, s, rtree, n_points, n_overlaps, delta):
        new_aj_ids, affected_aj_ids, n, no = [], set(), 0, 0
        for aj_id_in, aj_lon_lats in groupby(self._aj_lon_lat(s, new=True), key=lambda aj_lon_lat: aj_lon_lat[0]):
            aj_lon_lats = list(self._filter(aj_lon_lats))  # reuse below
            seen_posns = set()
            new_aj_ids.append(aj_id_in)
            affected_aj_ids.add(aj_id_in)
            for _, lon, lat in aj_lon_lats:
                posn = [(lon, lat)]
                for other_posn, aj_id_out in rtree.get_items(posn):
                    if other_posn not in seen_posns:
                        lo, hi = min(aj_id_in, aj_id_out), max(aj_id_in, aj_id_out)  # ordered pair
                        affected_aj_ids.add(aj_id_out)
                        n_overlaps[lo][hi] += 1
                        no += 1
                        seen_posns.add(other_posn)
            for _, lon, lat in aj_lon_lats:  # adding after avoids matching ourselves
                posn = [(lon, lat)]
                rtree[posn] = aj_id_in
                n_points[aj_id_in] += 1
                n += 1
                if n % delta == 0:
                    log.info(f'Measured {n} points')
        if n % delta:
            log.info(f'Measured {n} points')
        return new_aj_ids, affected_aj_ids

    def _filter(self, lon_lats):
        # todo - why random?  would sequential be better?
        for lon_lat in lon_lats:
            if uniform(0, 1 / self.fraction) < 1:
                yield lon_lat

    def _aj_lon_lat(self, s, new=True):
        from ..owners import SegmentReader
        lat = s.query(StatisticName.id). \
            filter(StatisticName.name == Names.LATITUDE,
                   StatisticName.owner == SegmentReader).scalar()
        lon = s.query(StatisticName.id). \
            filter(StatisticName.name == Names.LONGITUDE,
                   StatisticName.owner == SegmentReader).scalar()
        if not lat or not lon:
            log.warning(f'No {Names.LATITUDE} or {Names.LONGITUDE} in database')
            return

        # todo - use tables() instead
        sj_lat = inspect(StatisticJournal).local_table
        sj_lon = alias(inspect(StatisticJournal).local_table)
        sjf_lat = inspect(StatisticJournalFloat).local_table
        sjf_lon = alias(inspect(StatisticJournalFloat).local_table)
        aj = inspect(ActivityJournal).local_table
        ns = inspect(ActivitySimilarity).local_table

        existing_lo = select([ns.c.activity_journal_lo_id])
        existing_hi = select([ns.c.activity_journal_hi_id])
        existing = existing_lo.union(existing_hi).cte()

        # todo - has not been tuned for latest schema
        stmt = select([sj_lat.c.source_id, sjf_lon.c.value, sjf_lat.c.value]). \
            select_from(sj_lat).select_from(sj_lon).select_from(sjf_lat).select_from(sjf_lat).select_from(aj). \
            where(and_(sj_lat.c.source_id == sj_lon.c.source_id,  # same source
                       sj_lat.c.time == sj_lon.c.time,            # same time
                       sj_lat.c.source_id == aj.c.id,             # and associated with an activity
                       sj_lat.c.id == sjf_lat.c.id,               # lat sub-class
                       sj_lon.c.id == sjf_lon.c.id,               # lon sub-class
                       sj_lat.c.statistic_name_id == lat,
                       sj_lon.c.statistic_name_id == lon))

        if new:
            stmt = stmt.where(func.not_(sj_lat.c.source_id.in_(existing)))
        else:
            stmt = stmt.where(sj_lat.c.source_id.in_(existing))
        stmt = stmt.order_by(sj_lat.c.source_id)  # needed for seen logic
        yield from s.connection().execute(stmt)

    def _save(self, s, new_ids, affected_ids, n_points, n_overlaps, delta):
        distances = dict((s.source.id, s.value)
                         for s in s.query(StatisticJournalFloat).
                         join(StatisticName).
                         filter(StatisticName.name == Names.ACTIVE_DISTANCE,
                                StatisticName.owner == self.owner_in).all())  # todo - another owner
        n = 0
        for lo in affected_ids:
            add_lo, d_lo = lo in new_ids, distances.get(lo, None)
            if d_lo:
                for hi in (id for id in affected_ids if id > lo):
                    d_hi = distances.get(hi, None)
                    if d_hi and (add_lo or hi in new_ids):
                        if lo in new_ids and hi not in new_ids:
                            # hi already existed so was added first
                            n_max = n_points[hi]
                            d_factor = d_hi / d_lo if d_hi < d_lo else 1
                        else:
                            # both new and ordered lo-hi, or hi new and last
                            n_max = n_points[lo]
                            d_factor = d_lo / d_hi if d_lo < d_hi else 1
                        similarity = (n_overlaps[lo][hi] / n_max) * d_factor if n_max else 0
                        s.add(ActivitySimilarity(activity_journal_lo_id=lo, activity_journal_hi_id=hi,
                                                 similarity=similarity))
                        n += 1
                        if n % delta == 0:
                            log.info(f'Saved {n}')
        if n % delta:
            log.info(f'Saved {n}')


class NearbySimilarityDBSCAN(DBSCAN):

    def __init__(self, s, activity_group, epsilon, minpts):
        super().__init__(epsilon, minpts)
        self.__s = s
        self.__activity_group = activity_group
        ajlo = aliased(ActivityJournal)
        ajhi = aliased(ActivityJournal)
        self.__max_similarity = self.__s.query(func.max(ActivitySimilarity.similarity)). \
            join(ajlo, ActivitySimilarity.activity_journal_lo_id == ajlo.id). \
            join(ajhi, ActivitySimilarity.activity_journal_hi_id == ajhi.id). \
            filter(ajlo.activity_group == activity_group,
                   ajhi.activity_group == activity_group).scalar()
        if not self.__max_similarity: raise Exception('All activities unconnected')

    def run(self):
        candidates = set(x[0] for x in
                         self.__s.query(distinct(ActivitySimilarity.activity_journal_lo_id)).
                         join(ActivityJournal, ActivityJournal.id == ActivitySimilarity.activity_journal_lo_id).
                         filter(ActivityJournal.activity_group == self.__activity_group).all())
        candidates = candidates.union(set(x[0] for x in
                         self.__s.query(distinct(ActivitySimilarity.activity_journal_hi_id)).
                         join(ActivityJournal, ActivityJournal.id == ActivitySimilarity.activity_journal_hi_id).
                         filter(ActivityJournal.activity_group == self.__activity_group).all()))
        candidates = sorted(candidates)
        # shuffle(candidates)  # skip for repeatability
        return super().run(candidates)

    def neighbourhood(self, candidate, epsilon):
        qlo = self.__s.query(ActivitySimilarity.activity_journal_lo_id). \
            join(ActivityJournal, ActivityJournal.id == ActivitySimilarity.activity_journal_lo_id). \
            filter(ActivityJournal.activity_group == self.__activity_group,
                   ActivitySimilarity.activity_journal_hi_id == candidate,
                   (self.__max_similarity - ActivitySimilarity.similarity) / self.__max_similarity < epsilon)
        qhi = self.__s.query(ActivitySimilarity.activity_journal_hi_id). \
            join(ActivityJournal, ActivityJournal.id == ActivitySimilarity.activity_journal_hi_id). \
            filter(ActivityJournal.activity_group == self.__activity_group,
                   ActivitySimilarity.activity_journal_lo_id == candidate,
                   (self.__max_similarity - ActivitySimilarity.similarity) / self.__max_similarity < epsilon)
        return [x[0] for x in qlo.all()] + [x[0] for x in qhi.all()]


class NearbyCalculator(OwnerInMixin, ProcessCalculator):

    def _missing(self, s):
        # todo - should really be per-activity group (ie activity group per thread)
        latest_similarity = Timestamp.get(s, self.owner_in)
        latest_groups = Timestamp.get(s, self.owner_out)
        if not latest_groups or latest_similarity.time > latest_groups.time:
            self._delete(s)  # missing isn't really missing...
            return [True]
        else:
            return []

    def _delete(self, s):
        Timestamp.clear(s, self.owner_out)
        s.query(ActivityNearby).delete()

    def _run_one(self, s, missed):
        with Timestamp(owner=self.owner_out).on_success(s):
            for activity_group in s.query(ActivityGroup).all():
                try:
                    d_min, n = expand_max(0, 1, 5, lambda d: len(self.dbscan(s, d, activity_group)))
                    log.info(f'{n} groups at d={d_min}')
                    self.save(s, self.dbscan(s, d_min, activity_group), activity_group)
                except Exception as e:
                    log.warning(f'Failed to find nearby activities for {activity_group.name}: {e}')
                    log_current_exception(traceback=False)

    def dbscan(self, s, d, activity_group):
        return NearbySimilarityDBSCAN(s, activity_group, d, 3).run()

    def save(self, s, groups, activity_group):
        for i, group in enumerate(groups):
            log.info(f'Group {i} has {len(group)} members ({activity_group.name})')
            for activity_journal_id in group:
                s.add(ActivityNearby(group=i, activity_journal_id=activity_journal_id))
