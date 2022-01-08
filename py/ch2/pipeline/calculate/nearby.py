from logging import getLogger

from sqlalchemy import distinct

from .utils import ProcessCalculator
from ..pipeline import OwnerInMixin
from ...common.log import log_current_exception
from ...lib.dbscan import DBSCAN
from ...lib.optimizn import expand_max
from ...sql import ActivityJournal, ActivityGroup, ActivityDistance, ActivityNearby, Timestamp

log = getLogger(__name__)


class NearbyDBSCAN(DBSCAN):

    def __init__(self, s, epsilon, minpts):
        super().__init__(epsilon, minpts)
        self.__s = s

    def run(self):
        candidates = set(x[0] for x in
                         self.__s.query(distinct(ActivityDistance.activity_journal_lo_id)).all())
        candidates = candidates.union(set(x[0] for x in
                                          self.__s.query(distinct(ActivityDistance.activity_journal_hi_id)).all()))
        candidates = sorted(candidates)
        # shuffle(candidates)  # skip for repeatability
        return super().run(candidates)

    def neighbourhood(self, candidate, epsilon):
        qlo = self.__s.query(ActivityDistance.activity_journal_lo_id). \
            filter(ActivityDistance.activity_journal_hi_id == candidate,
                   ActivityDistance.distance < epsilon)
        qhi = self.__s.query(ActivityDistance.activity_journal_hi_id). \
            filter(ActivityDistance.activity_journal_lo_id == candidate,
                   ActivityDistance.distance < epsilon)
        neighbourhood = [x[0] for x in qlo.all()] + [x[0] for x in qhi.all()]
        log.debug(f'Neighbourhood of {len(neighbourhood)} for {candidate} at {epsilon}')
        return neighbourhood


class NearbyCalculator(OwnerInMixin, ProcessCalculator):

    def _missing(self, s):
        latest_distance = Timestamp.get(s, self.owner_in)
        latest_nearby = Timestamp.get(s, self.owner_out)
        if not latest_nearby or latest_distance.time > latest_nearby.time:
            self._delete(s)  # missing isn't really missing...
            return ['missing']
        else:
            return []

    def _delete(self, s):
        Timestamp.clear(s, self.owner_out)
        s.query(ActivityNearby).delete()

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            with Timestamp(owner=self.owner_out).on_success(s):
                try:
                    d_min, n = expand_max(0, 10000, 5, lambda d: len(self.dbscan(s, d)))
                    log.info(f'{n} groups at d={d_min}')
                    self.save(s, self.dbscan(s, d_min))
                except Exception as e:
                    log.warning(f'Failed to find nearby activities: {e}')
                    log_current_exception(traceback=False)

    def dbscan(self, s, d):
        return NearbyDBSCAN(s, d, 3).run()

    def save(self, s, groups):
        for i, group in enumerate(groups):
            log.info(f'Group {i} has {len(group)} members')
            for activity_journal_id in group:
                s.add(ActivityNearby(group=i, activity_journal_id=activity_journal_id))
