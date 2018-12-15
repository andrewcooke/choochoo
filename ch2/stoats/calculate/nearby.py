
from collections import defaultdict
from random import shuffle

from sqlalchemy import inspect, select, alias, and_, distinct, func

from .. import DbPipeline
from ..names import LONGITUDE, LATITUDE
from ...arty import MatchType
from ...arty.spherical import SQRTree
from ...lib.date import to_time
from ...lib.dbscan import DBSCAN
from ...lib.optimizn import expand_max
from ...squeal.tables.activity import ActivityJournal, ActivityGroup
from ...squeal.tables.nearby import NearbySimilarity
from ...squeal.tables.statistic import StatisticName, StatisticJournal, StatisticJournalFloat


class NearbySimilarityCalculator(DbPipeline):

    def run(self, force=False, after=None):
        label = self._assert_karg('label', 'default')
        border = self._assert_karg('border', 3)
        rtree = SQRTree(default_match=MatchType.INTERSECTS, default_border=border)

        with self._db.session_context() as s:
            if force:
                self._delete(s, label)
            n_points = defaultdict(lambda: 0)
            self._prepare(s, label, rtree, n_points, 10000)
            n_intersects = defaultdict(lambda: defaultdict(lambda: 0))
            new_ids = self._measure(s, label, rtree, n_points, n_intersects, 1000)
            self._save(s, label, new_ids, n_points, n_intersects)

    def _delete(self, s, label):
        self._log.warn('Deleting similarity data for %s' % label)
        s.query(NearbySimilarity). \
            filter(NearbySimilarity.label == label). \
            delete()

    def _save(self, s, label, new_ids, n_points, n_intersects):
        n, total = 0, (len(new_ids) * (len(new_ids) - 1)) / 2
        for lo in new_ids:
            for hi in filter(lambda hi: hi > lo, new_ids):
                s.add(NearbySimilarity(label=label, activity_journal_lo_id=lo, activity_journal_hi_id=hi,
                                       similarity=n_intersects[lo][hi] / (n_points[lo] + n_points[hi])))
                n += 1
                if n % 100 == 0:
                    self._log.info('Saved %d / %d' % (n, total))

    def _prepare(self, s, label, rtree, n_points, delta):
        n = 0
        for id_in, lon, lat in self._data(s, label, new=False):
            p = [(lon, lat)]
            rtree[p] = id_in
            n_points[id_in] += 1
            n += 1
            if n % delta == 0:
                self._log.info('Loaded %s points' % n)

    def _measure(self, s, label, rtree, n_points, n_intersects, delta):
        new_ids, current_id, seen, n = [], None, None, 0
        for id_in, lon, lat in self._data(s, label, new=True):
            if id_in != current_id:
                current_id, seen = id_in, set()
                new_ids.append(id_in)
            p = [(lon, lat)]
            for other_p, id_out in rtree.get_items(p):
                if id_in != id_out:
                    if other_p not in seen:
                        lo, hi = min(id_in, id_out), max(id_in, id_out)
                        n_intersects[lo][hi] += 1
                        seen.add(other_p)
            rtree[p] = id_in
            n_points[id_in] += 1
            n += 1
            if n % delta == 0:
                self._log.info('Measured %s points' % n)
        return new_ids

    def _data(self, s, label, new=True):

        activity_group = self._assert_karg('activity_group', 'Bike')
        start = to_time(self._assert_karg('start', '1970'))
        finish = to_time(self._assert_karg('finish', '2999'))
        latitude = self._assert_karg('latitude', -33)
        longitude = self._assert_karg('longitude', -70)
        height = self._assert_karg('height', 10)
        width = self._assert_karg('width', 10)

        lat = s.query(StatisticName.id).filter(StatisticName.name == LATITUDE).scalar()
        lon = s.query(StatisticName.id).filter(StatisticName.name == LONGITUDE).scalar()
        agroup = s.query(ActivityGroup.id).filter(ActivityGroup.name == activity_group).scalar()

        sj_lat = inspect(StatisticJournal).local_table
        sj_lon = alias(inspect(StatisticJournal).local_table)
        sjf_lat = inspect(StatisticJournalFloat).local_table
        sjf_lon = alias(inspect(StatisticJournalFloat).local_table)
        aj = inspect(ActivityJournal).local_table
        ns = inspect(NearbySimilarity).local_table

        existing_lo = select([ns.c.activity_journal_lo_id]). \
            where(ns.c.label == label)
        existing_hi = select([ns.c.activity_journal_hi_id]). \
            where(ns.c.label == label)
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
                       sjf_lat.c.value > latitude - height / 2,   # spatial limits
                       sjf_lat.c.value < latitude + height / 2,
                       sjf_lon.c.value > longitude - width / 2,
                       sjf_lon.c.value < longitude + width / 2))

        if new:
            stmt = stmt.where(func.not_(sj_lat.c.source_id.in_(existing)))
        else:
            stmt = stmt.where(sj_lat.c.source_id.in_(existing))
        stmt = stmt.order_by(sj_lat.c.source_id)  # needed for seen logic
        yield from s.connection().execute(stmt)


class NearbySimilarityDBSCAN(DBSCAN):

    def __init__(self, log, s, label, epsilon, minpts):
        super().__init__(log, epsilon, minpts)
        self.__s = s
        self.__label = label
        self.__max_similarity = self.__s.query(func.max(NearbySimilarity.similarity)). \
            filter(NearbySimilarity.label == label).scalar()
        # self._log.info('Max similarity %.2f' % self.__max_similarity)

    def run(self):
        candidates = [x[0] for x in
                      self.__s.query(distinct(NearbySimilarity.activity_journal_lo_id)).
                          filter(NearbySimilarity.label == self.__label).all()]
        shuffle(candidates)
        return super().run(candidates)

    def neighbourhood(self, candidate, epsilon):
        qlo = self.__s.query(NearbySimilarity.activity_journal_lo_id). \
            filter(NearbySimilarity.label == self.__label,
                   NearbySimilarity.activity_journal_hi_id == candidate,
                   (self.__max_similarity - NearbySimilarity.similarity) / self.__max_similarity < epsilon)
        qhi =  self.__s.query(NearbySimilarity.activity_journal_hi_id). \
            filter(NearbySimilarity.label == self.__label,
                   NearbySimilarity.activity_journal_lo_id == candidate,
                   (self.__max_similarity - NearbySimilarity.similarity) / self.__max_similarity < epsilon)
        return [x[0] for x in qlo.all()] + [x[0] for x in qhi.all()]


if __name__ == '__main__':

    from ch2.squeal.database import connect
    from ch2.data import Data

    ns, log, db = connect(['-v', '5'])
    data = Data(log, db)
    label = 'test5'

    with db.session_context() as s:
        d_min, _ = expand_max(0, 1, 5,
                              lambda d: len(NearbySimilarityDBSCAN(log, s, label, d, 3).run()))
        for group in NearbySimilarityDBSCAN(log, s, label, d_min, 3).run():
            print(group)
