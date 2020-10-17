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
with srid as (select s.id as sector_id,
                     st_setsrid(s.route, sg.srid) as sector,
                     st_transform(aj.route_t::geometry, sg.srid) as route_t,
                     st_setsrid(s.start, sg.srid) as start,
                     st_setsrid(s.finish, sg.srid) as finish
                from sector as s,
                     activity_journal as aj,
                     sector_group as sg
               where s.sector_group_id = sg.id
                 and sg.id = :sector_group_id
                 and aj.id = :activity_journal_id
                 and st_intersects(st_setsrid(s.hull, sg.srid), st_transform(aj.route_t::geometry, sg.srid))),
     start_point as (select r.sector_id,
                            r.route_t,
                            (st_dump(st_multi(st_intersection(r.start, r.route_t)))).geom as point
                       from srid as r),
     start_fraction as (select p.sector_id,
                               st_linelocatepoint(p.route_t, p.point) as fraction
                          from start_point as p),
     finish_point as (select r.sector_id,
                             r.route_t,
                             (st_dump(st_multi(st_intersection(r.finish, r.route_t)))).geom as point
                        from srid as r),
     finish_fraction as (select p.sector_id,
                                st_linelocatepoint(p.route_t, p.point) as fraction
                           from finish_point as p)
select r.sector_id,
       s.fraction as start_fraction,
       f.fraction as finish_fraction,
       aj.start + interval '1' second * st_m(st_lineinterpolatepoint(r.route_t, s.fraction)) as start,
       aj.start + interval '1' second * st_m(st_lineinterpolatepoint(r.route_t, f.fraction)) as finish
  from srid as r,
       start_fraction as s,
       finish_fraction as f,
       activity_journal as aj
 where aj.id = :activity_journal_id
   and s.fraction < f.fraction
   and s.sector_id = f.sector_id
   and s.sector_id = r.sector_id
   and st_length(st_linesubstring(r.route_t, s.fraction, f.fraction)) 
       between 0.95 * st_length(r.sector) and 1.05 * st_length(r.sector)
''')
        log.debug(sql)
        result = s.connection().execute(sql, sector_group_id=sector_group.id, activity_journal_id=ajournal.id)
        for row in result.fetchall():
            data = {name: value for name, value in zip(result.keys(), row)}
            sjournal = add(s, SectorJournal(activity_journal_id=ajournal.id, activity_group=ajournal.activity_group,
                                            **data))
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
