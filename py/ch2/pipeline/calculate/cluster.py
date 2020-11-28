from .utils import ProcessCalculator, RerunWhenNewActivitiesMixin
from ...data.cluster import hulls_from_last_activity, sectors_from_hulls
from ...sql import Timestamp
from ...sql.tables.sector import DEFAULT_GROUP_RADIUS_KM


class ClusterCalculator(RerunWhenNewActivitiesMixin, ProcessCalculator):

    def __init__(self, *args, excess=0.1, radius_km=DEFAULT_GROUP_RADIUS_KM, **kargs):
        super().__init__(*args, excess=excess, **kargs)
        self.__radius_km = radius_km

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            with Timestamp(owner=self.owner_out).on_success(s):
                sector_group = hulls_from_last_activity(s, self.__radius_km)
                if sector_group:
                    sectors_from_hulls(s, sector_group)


