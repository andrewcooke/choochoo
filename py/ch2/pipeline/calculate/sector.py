from logging import getLogger

from sqlalchemy import func

from ch2.common.date import local_time_to_time
from ch2.data.sector import find_sector_journals, add_sector_statistics
from ch2.pipeline.calculate.utils import ActivityJournalProcessCalculator, ProcessCalculator, ActivityOwnerProcessCalculator
from ch2.pipeline.pipeline import LoaderMixin, OwnerInMixin
from ch2.sql import Timestamp, ActivityJournal
from ch2.sql.database import connect_config
from ch2.sql.tables.sector import SectorGroup, Sector, SectorClimb, SectorJournal
from ch2.sql.types import Point, short_cls

log = getLogger(__name__)


class SectorCalculator(LoaderMixin, ActivityOwnerProcessCalculator):
    '''
    Run through new activity journals, find any sectors that match, populate the SectorJournal,
    and add associated statistics.
    '''

    def _startup(self, s):
        super()._startup(s)
        Sector.provides(s, self)
        SectorClimb.provides(s, self)
        SectorJournal.clean(s)

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal, constraint=self.owner_in).on_success(s):
                self._run_activity_journal(s, ajournal)

    def _run_activity_journal(self, s, ajournal):
        if ajournal.route_edt:
            for sector_group in s.query(SectorGroup). \
                    filter(func.ST_Distance(SectorGroup.centre, Point.fmt(ajournal.centre)) < SectorGroup.radius). \
                    all():
                count = 0
                for sjournal in find_sector_journals(s, sector_group, ajournal, self.owner_in):
                    loader = self._get_loader(s, add_serial=False)
                    add_sector_statistics(s, sjournal, loader)
                    loader.load()
                    count += 1
                if count:
                    log.info(f'Found {count} sectors for activity on {ajournal.start}')


if __name__ == '__main__':
    config = connect_config(['-v5'])
    pipeline = SectorCalculator(config)
    with config.db.session_context() as s:
        ajournal = s.query(ActivityJournal).filter(ActivityJournal.id == 1799).one()
        pipeline._run_activity_journal(s, ajournal)
