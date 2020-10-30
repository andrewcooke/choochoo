from ch2.data.cluster import hulls_from_last_activity, sectors_from_hulls
from ch2.pipeline.calculate.utils import ProcessCalculator, RerunWhenNewActivitiesMixin
from ch2.sql import Timestamp
from ch2.sql.database import connect_config
from ch2.sql.types import short_cls


class ClusterCalculator(RerunWhenNewActivitiesMixin, ProcessCalculator):

    def __init__(self, *args, excess=0.1, radius_km=200, **kargs):
        super().__init__(*args, excess=excess, **kargs)
        self.__radius_km = radius_km

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            with Timestamp(owner=self.owner_out).on_success(s):
                sector_group = hulls_from_last_activity(s, self.__radius_km)
                sectors_from_hulls(s, sector_group)


if __name__ == '__main__':
    from ch2.pipeline.calculate.sector import SectorCalculator
    config = connect_config(['-v5'])
    # ClusterCalculator(config, owner_in=short_cls(ActivityReader)).run()
    SectorCalculator(config, owner_in=short_cls(ClusterCalculator)).run()
