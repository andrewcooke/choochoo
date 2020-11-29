from json import loads
from logging import getLogger

from sqlalchemy import func, text

from .power import PowerModel
from .utils import ActivityGroupProcessCalculator, ProcessCalculator
from ..pipeline import LoaderMixin
from ...common.date import local_time_to_time
from ...data.sector import find_and_add_sector_journals, add_sector_statistics
from ...names import simple_name
from ...sql import Timestamp, Constant, ActivityJournal
from ...sql.tables.sector import SectorGroup, Sector, SectorClimb, SectorJournal

log = getLogger(__name__)


class SectorCalculator(LoaderMixin, ActivityGroupProcessCalculator):
    '''
    Run through new activity journals, find any sectors that match, populate the SectorJournal,
    and add associated statistics.
    '''

    def __init__(self, *args, power_model=None, **kargs):
        super().__init__(*args, **kargs)
        self.__power_model_ref = power_model

    def _startup(self, s):
        super()._startup(s)
        Sector.provides(s, self)
        SectorClimb.provides(s, self)
        SectorJournal.clean(s)
        if self.__power_model_ref:
            self.__power_model = PowerModel(**loads(Constant.from_name(s, self.__power_model_ref).at(s).value))
        else:
            log.warning('No power model configured for sectors')
            self.__power_model = None

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            if self.__power_model:
                power_model = self.__power_model.expand(s, ajournal.start, default_owner=Constant,
                                                        default_activity_group=self.activity_group)
            else:
                power_model = None
            log.debug(f'Power: {self.__power_model_ref}: {power_model}')
            with Timestamp(owner=self.owner_out, source=ajournal, constraint=self.activity_group).on_success(s):
                self._run_activity_journal(s, ajournal, power_model)

    def _run_activity_journal(self, s, ajournal, power_model):
        if ajournal.route_edt:
            for sector_group in s.query(SectorGroup). \
                    filter(func.ST_Distance(SectorGroup.centre, ajournal.centre) < SectorGroup.radius). \
                    all():
                count = 0
                for sjournal in find_and_add_sector_journals(s, sector_group, ajournal):
                    loader = self._get_loader(s, add_serial=False)
                    add_sector_statistics(s, sjournal, loader, power_model=power_model)
                    loader.load()
                    count += 1
                if count:
                    log.info(f'Found {count} sectors for activity on {ajournal.start}')


class NewSectorCalculator(LoaderMixin, ProcessCalculator):

    def __init__(self, *args, activity_group=None, new_sector_id=None, **kargs):
        super().__init__(*args, **kargs)
        self.activity_group = self._assert('activity_group', activity_group)
        self.new_sector_id = int(self._assert('new_sector_id', new_sector_id))

    def _startup(self, s):
        super()._startup(s)
        SectorJournal.clean(s)
        self.sector = s.query(Sector).filter(Sector.id == int(self.new_sector_id)).one()
        self.sector.sector_group  # eager load
        # we don't provide anything because they are statistics identical to those already declared by
        # SectorCalculator

    def _missing(self, s):
        q = text('''
select aj.id
  from activity_journal as aj,
       source as sc,
       activity_group as ag,
       sector as s,
       sector_group as sg
 where s.id = :new_sector_id
   and s.sector_group_id = sg.id
   and st_distance(sg.centre, aj.centre) < sg.radius
   and sc.id = aj.id
   and ag.id = sc.activity_group_id
   and ag.name = :activity_group
   and aj.route_edt is not null
        ''')
        log.debug(q)
        log.debug(f'new_sector_id: {self.new_sector_id}; activity_group: {self.activity_group}')
        return [str(row[0]) for row in
                s.connection().execute(q, new_sector_id=self.new_sector_id,
                                       activity_group=simple_name(self.activity_group)).fetchall()]

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            count = 0
            ajournal = s.query(ActivityJournal).filter(ActivityJournal.id == int(missed)).one()
            for sjournal in find_and_add_sector_journals(s, self.sector.sector_group, ajournal,
                                                         sector_id=self.new_sector_id):
                # fake owner - we're patching in the above for new sectors
                loader = self._get_loader(s, add_serial=False, owner=SectorCalculator)
                # no need for power_model - called for user-defined sectors, not climbs
                add_sector_statistics(s, sjournal, loader)
                loader.load()
                count += 1
            if count:
                log.info(f'Found {count} sectors for activity on {ajournal.start}')
