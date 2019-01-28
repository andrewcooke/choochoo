
from collections import defaultdict, namedtuple
from itertools import groupby
from json import loads

from sqlalchemy import inspect, select, alias, and_, distinct, func

from .. import DbPipeline
from ..names import LONGITUDE, LATITUDE, ACTIVE_DISTANCE
from ...arty import MatchType
from ...arty.spherical import SQRTree
from ...lib.date import to_time
from ...lib.dbscan import DBSCAN
from ...lib.optimizn import expand_max
from ...squeal.tables.activity import ActivityJournal, ActivityGroup
from ...squeal.tables.constant import Constant
from ...squeal.tables.nearby import ActivitySimilarity, ActivityNearby
from ...squeal.tables.statistic import StatisticName, StatisticJournal, StatisticJournalFloat
from ...stoats.calculate.activity import ActivityStatistics

Nearby = namedtuple('Nearby', 'constraint, activity_group, border, start, finish, '
                              'latitude, longitude, height, width')


class NearbySimilarityCalculator(DbPipeline):

    def _on_init(self, *args, **kargs):
        super()._on_init(*args, **kargs)
        nearby = self._assert_karg('nearby')
        with self._db.session_context() as s:
            self._config = Nearby(**loads(Constant.get(s, nearby).at(s).value))
        self._log.info('%s: %s' % (nearby, self._config))

    def run(self, force=False, after=None):

        rtree = SQRTree(default_match=MatchType.INTERSECTS, default_border=self._config.border)

        with self._db.session_context() as s:
            if force:
                self._delete(s)
            n_points = defaultdict(lambda: 0)
            self._prepare(s, rtree, n_points, 30000)
            n_intersects = defaultdict(lambda: defaultdict(lambda: 0))
            new_ids, affected_ids = self._count_overlaps(s, rtree, n_points, n_intersects, 10000)
            self._save(s, new_ids, affected_ids, n_points, n_intersects, 10000)

    def _delete(self, s):
        self._log.warning('Deleting similarity data for %s' % self._config.constraint)
        s.query(ActivitySimilarity). \
            filter(ActivitySimilarity.constraint == self._config.constraint). \
            delete()

    def _save(self, s, new_ids, affected_ids, n_points, n_intersects, delta):
        distances = dict((s.source.id, s.value)
                         for s in s.query(StatisticJournalFloat).
                         join(StatisticName).
                         filter(StatisticName.name == ACTIVE_DISTANCE,
                                StatisticName.owner == ActivityStatistics).all())
        n = 0
        import pdb; pdb.set_trace()
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
                        s.add(ActivitySimilarity(constraint=self._config.constraint,
                                                 activity_journal_lo_id=lo, activity_journal_hi_id=hi,
                                                 similarity=(n_intersects[lo][hi] / n_max) * d_factor))
                        n += 1
                        if n % delta == 0:
                            self._log.info('Saved %d for %s' % (n, self._config.constraint))
        if n % delta:
            self._log.info('Saved %d for %s' % (n, self._config.constraint))

    def _prepare(self, s, rtree, n_points, delta):
        n = 0
        for aj_id_in, lon, lat in self._aj_lon_lat(s, new=False):
            posn = [(lon, lat)]
            rtree[posn] = aj_id_in
            n_points[aj_id_in] += 1
            n += 1
            if n % delta == 0:
                self._log.info('Loaded %s points for %s' % (n, self._config.constraint))
        if n % delta:
            self._log.info('Loaded %s points for %s' % (n, self._config.constraint))

    def _count_overlaps(self, s, rtree, n_points, n_intersects, delta):
        new_aj_ids, affected_aj_ids, n = [], set(), 0
        for aj_id_in, aj_lon_lats in groupby(self._aj_lon_lat(s, new=True), key=lambda aj_lon_lat: aj_lon_lat[0]):
            aj_lon_lats = list(aj_lon_lats)  # reuse below
            seen_posns = set()
            new_aj_ids.append(aj_id_in)
            affected_aj_ids.add(aj_id_in)
            for _, lon, lat in aj_lon_lats:
                posn = [(lon, lat)]
                for other_posn, aj_id_out in rtree.get_items(posn):
                    if other_posn not in seen_posns:
                        lo, hi = min(aj_id_in, aj_id_out), max(aj_id_in, aj_id_out)  # ordered pair
                        affected_aj_ids.add(aj_id_out)
                        n_intersects[lo][hi] += 1
                        seen_posns.add(other_posn)
            for _, lon, lat in aj_lon_lats:  # adding after avoids matching ourselves
                posn = [(lon, lat)]
                rtree[posn] = aj_id_in
                n_points[aj_id_in] += 1
                n += 1
                if n % delta == 0:
                    self._log.info('Measured %s points for %s' % (n, self._config.constraint))
        if n % delta:
            self._log.info('Measured %s points for %s' % (n, self._config.constraint))
        return new_aj_ids, affected_aj_ids

    def _aj_lon_lat(self, s, new=True):

        start = to_time(self._config.start)
        finish = to_time(self._config.finish)

        lat = s.query(StatisticName.id).filter(StatisticName.name == LATITUDE).scalar()
        lon = s.query(StatisticName.id).filter(StatisticName.name == LONGITUDE).scalar()
        agroup = s.query(ActivityGroup.id).filter(ActivityGroup.name == self._config.activity_group).scalar()

        sj_lat = inspect(StatisticJournal).local_table
        sj_lon = alias(inspect(StatisticJournal).local_table)
        sjf_lat = inspect(StatisticJournalFloat).local_table
        sjf_lon = alias(inspect(StatisticJournalFloat).local_table)
        aj = inspect(ActivityJournal).local_table
        ns = inspect(ActivitySimilarity).local_table

        existing_lo = select([ns.c.activity_journal_lo_id]). \
            where(ns.c.constraint == self._config.constraint)
        existing_hi = select([ns.c.activity_journal_hi_id]). \
            where(ns.c.constraint == self._config.constraint)
        existing = existing_lo.union(existing_hi).cte()

        stmt = select([sj_lat.c.source_id, sjf_lon.c.value, sjf_lat.c.value]). \
            select_from(sj_lat).select_from(sj_lon).select_from(sjf_lat).select_from(sjf_lat).select_from(aj). \
            where(and_(sj_lat.c.source_id == sj_lon.c.source_id,  # same source
                       sj_lat.c.time == sj_lon.c.time,            # same time
                       sj_lat.c.source_id == aj.c.id,             # and associated with an activity
                       aj.c.activity_group_id == agroup,          # of the right group
                       sj_lat.c.id == sjf_lat.c.id,               # lat sub-class
                       sj_lon.c.id == sjf_lon.c.id,               # lon sub-class
                       sj_lat.c.statistic_name_id == lat,         # lat name
                       sj_lon.c.statistic_name_id == lon,         # lon name
                       sj_lat.c.time >= start.timestamp(),        # time limits
                       sj_lat.c.time < finish.timestamp(),
                       sjf_lat.c.value > self._config.latitude - self._config.height / 2,
                       sjf_lat.c.value < self._config.latitude + self._config.height / 2,
                       sjf_lon.c.value > self._config.longitude - self._config.width / 2,
                       sjf_lon.c.value < self._config.longitude + self._config.width / 2))

        if new:
            stmt = stmt.where(func.not_(sj_lat.c.source_id.in_(existing)))
        else:
            stmt = stmt.where(sj_lat.c.source_id.in_(existing))
        stmt = stmt.order_by(sj_lat.c.source_id)  # needed for seen logic
        yield from s.connection().execute(stmt)


class NearbySimilarityDBSCAN(DBSCAN):

    def __init__(self, log, s, constraint, epsilon, minpts):
        super().__init__(log, epsilon, minpts)
        self.__s = s
        self.__constraint = constraint
        self.__max_similarity = self.__s.query(func.max(ActivitySimilarity.similarity)). \
            filter(ActivitySimilarity.constraint == constraint).scalar()
        # self._log.info('Max similarity %.2f' % self.__max_similarity)

    def run(self):
        candidates = set(x[0] for x in
                         self.__s.query(distinct(ActivitySimilarity.activity_journal_lo_id)).
                         filter(ActivitySimilarity.constraint == self.__constraint).all())
        candidates.union(set(x[0] for x in
                             self.__s.query(distinct(ActivitySimilarity.activity_journal_lo_id)).
                             filter(ActivitySimilarity.constraint == self.__constraint).all()))
        candidates = sorted(candidates)
        # shuffle(candidates)  # skip for repeatability
        return super().run(candidates)

    def neighbourhood(self, candidate, epsilon):
        qlo = self.__s.query(ActivitySimilarity.activity_journal_lo_id). \
            filter(ActivitySimilarity.constraint == self.__constraint,
                   ActivitySimilarity.activity_journal_hi_id == candidate,
                   (self.__max_similarity - ActivitySimilarity.similarity) / self.__max_similarity < epsilon)
        qhi = self.__s.query(ActivitySimilarity.activity_journal_hi_id). \
            filter(ActivitySimilarity.constraint == self.__constraint,
                   ActivitySimilarity.activity_journal_lo_id == candidate,
                   (self.__max_similarity - ActivitySimilarity.similarity) / self.__max_similarity < epsilon)
        return [x[0] for x in qlo.all()] + [x[0] for x in qhi.all()]


class NearbyStatistics(NearbySimilarityCalculator):

    def run(self, force=False, after=None):
        super().run(force=force, after=after)
        with self._db.session_context() as s:
            d_min, n = expand_max(self._log, 0, 1, 5, lambda d: len(self.dbscan(s, d)))
            self._log.info('%d groups at d=%f' % (n, d_min))
            self.save(s, self.dbscan(s, d_min))

    def dbscan(self, s, d):
        return NearbySimilarityDBSCAN(self._log, s, self._config.constraint, d, 3).run()

    def save(self, s, groups):
        s.query(ActivityNearby). \
            filter(ActivityNearby.constraint == self._config.constraint).delete()
        for i, group in enumerate(groups):
            self._log.info('Group %d has %d members' % (i, len(group)))
            for activity_journal_id in group:
                s.add(ActivityNearby(constraint=self._config.constraint, group=i,
                                     activity_journal_id=activity_journal_id))
