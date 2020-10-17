from logging import getLogger

from sqlalchemy import text, func

from ch2.sql.database import connect_config
from ch2.pipeline.calculate.utils import ActivityJournalCalculatorMixin, ProcessCalculator
from ch2.pipeline.pipeline import LoaderMixin
from ch2.common.date import local_time_to_time
from ch2.sql import Timestamp, ActivityJournal
from ch2.sql.tables.sector import SectorGroup, SectorJournal, Sector, SectorClimb
from ch2.sql.utils import add

log = getLogger(__name__)


class FindSectorCalculator(LoaderMixin, ActivityJournalCalculatorMixin, ProcessCalculator):
    '''
    Run through new activity journals, find any sectors that match, populate the SectorJournal,
    and add associated statistics.
    '''

    def _startup(self, s):
        super()._startup(s)
        Sector.provides(s, self)
        SectorClimb.provides(s, self)

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                self._run_activity_journal(s, ajournal)

    def _run_activity_journal(self, s, ajournal):
        if ajournal.route_edt:
            for sector_group in s.query(SectorGroup). \
                    filter(func.ST_Distance(SectorGroup.centre, ajournal.centre) < SectorGroup.radius). \
                    all():
                count = 0
                for sjournal in self.__load_matches(s, sector_group, ajournal):
                    self.__add_statistics(s, sjournal)
                    count += 1
                if count:
                    log.info(f'Found {count} sectors for activity on {ajournal.start}')

    def __load_matches(self, s, sector_group, ajournal):
        sql = text('''
with hull as (select s.id as sector_id,
                     st_setsrid(s.route, sg.srid) as sector,
                     st_buffer(st_setsrid(s.route, sg.srid), 20, 'endcap=flat') as hull
                from sector as s,
                     sector_group as sg
               where sg.id = :sector_group_id),
     candidate as (select h.sector_id,
                          h.sector,
                          st_transform(aj.route_t::geometry, sg.srid) as route,
                          (st_dump(st_multi(st_intersection(st_transform(aj.route_t::geometry, sg.srid), h.hull)))).geom as candidate
                     from hull as h,
                          activity_journal as aj,
                          sector_group as sg
                    where aj.id = :activity_journal_id
                      and sg.id = :sector_group_id),
     statistic as (select c.sector_id,
                          c.route,
                          aj.start as t0,
                          cos(st_angle(c.sector, c.candidate)) as similarity,
                          st_length(c.sector) as target_length,
                          st_length(c.candidate) as candidate_length,
                          st_linelocatepoint(c.route, st_startpoint(c.candidate)) as start_fraction,
                          st_linelocatepoint(c.route, st_endpoint(c.candidate)) as finish_fraction
                     from candidate as c,
                          activity_journal as aj
                    where not st_isempty(candidate)
                      and aj.id = :activity_journal_id)
select sector_id,
       t0 + interval '1' second * st_m(st_lineinterpolatepoint(route, greatest(0, least(1, start_fraction)))) as start,
       t0 + interval '1' second * st_m(st_lineinterpolatepoint(route, greatest(0, least(1, finish_fraction)))) as finish,
       start_fraction, finish_fraction
  from statistic
 where similarity > 0.9
   and candidate_length between 0.9 * target_length and 1.1 * target_length;
''')
        log.debug(sql)
        result = s.connection().execute(sql, sector_group_id=sector_group.id, activity_journal_id=ajournal.id)
        for row in result.fetchall():
            data = {name: value for name, value in zip(result.keys(), row)}
            sjournal = add(s, SectorJournal(activity_journal_id=ajournal.id, activity_group=ajournal.activity_group, **data))
            s.commit()
            yield sjournal

    def __add_statistics(self, s, sjournal):
        loader = self._get_loader(s, add_serial=False)
        # delegate to the sector since that can be subclassed (eg climb)
        sjournal.sector.add_statistics(s, sjournal, loader)
        loader.load()


if __name__ == '__main__':
    config = connect_config(['-v5'])
    pipeline = FindSectorCalculator(config)
    with config.db.session_context() as s:
        import pdb; pdb.set_trace()
        ajournal = s.query(ActivityJournal).filter(ActivityJournal.id == 1799).one()
        pipeline._run_activity_journal(s, ajournal)
