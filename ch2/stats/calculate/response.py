
import datetime as dt
from collections import namedtuple
from json import loads
from logging import getLogger

from math import log10
from sqlalchemy.sql.functions import count

from ch2.data.response import sum_to_hour, calc_response
from . import UniProcCalculator
from ...data.frame import statistics
from ...lib.date import round_hour, to_time, local_date_to_time, now
from ...sql import ActivityGroup
from ...sql import StatisticJournal, Composite, StatisticName, Source, Constant, CompositeComponent, \
    StatisticJournalFloat
from ...sql.utils import add
from ...stats.names import _src, ALL, HR_IMPULSE_10
from ...stats.pipeline import LoaderMixin

log = getLogger(__name__)

Response = namedtuple('Response', 'src_owner, dest_name, tau_days, start, scale')


class ResponseCalculator(LoaderMixin, UniProcCalculator):
    '''
    this is hard to do correctly, incrementally.

    for now, we do all or nothing.

    first, we check if the current solution is complete:
    * all sources used (no need to check for gaps - composite chaining should do that)
    * within 3 hours of the current time (if not, we regenerate, padding with zeroes)

    if not complete, we regenerate the whole damn thing.
    '''

    def __init__(self, *args, responses_ref=None, **kargs):
        self.responses_ref = self._assert('responses_ref', responses_ref)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        super()._startup(s)
        constants = [Constant.get(s, response) for response in self.responses_ref]
        self.responses = [Response(**loads(constant.at(s).value)) for constant in constants]

    def _delete(self, s):
        start, finish = self._start_finish(local_date_to_time)
        if start or self.force:
            if finish:
                log.warning(f'Ignoring finish - will delete all impulses from {start} onwards')
            self._delete_from(s, start)

    def _delete_from(self, s, start=None, inclusive=True):
        composite_ids = s.query(Composite.id). \
            join(StatisticJournal, Composite.id == StatisticJournal.source_id). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.owner == self.owner_out)
        if start:
            if inclusive:
                composite_ids = composite_ids.filter(StatisticJournal.time >= start)
            else:
                composite_ids = composite_ids.filter(StatisticJournal.time > start)
        log.debug(f'Delete query: {composite_ids}')
        n = s.query(count(Source.id)). \
            filter(Source.id.in_(composite_ids)). \
            scalar()
        if n:
            log.warning(f'Deleting {n} Composite sources ({start} onwards{" inclusive" if inclusive else ""})')
            s.query(Source). \
                filter(Source.id.in_(composite_ids)). \
                delete(synchronize_session=False)
            s.commit()

    def _missing(self, s):
        # clean out any gaps by unzipping the chained composites
        Composite.clean(s)
        # range we expect data for
        missing_sources = self.__missing_sources(s)
        finish = round_hour(dt.datetime.now(tz=dt.timezone.utc), up=True)
        missing_recent = any(self.__missing_recent(s, response.dest_name, finish) for response in self.responses)
        if missing_recent or missing_sources:
            if missing_recent: log.info('Incomplete coverage (so will re-calculate)')
            if missing_sources: log.info('Additional sources (so will re-calculate)')
            self._delete_from(s)
            start = round_hour(self.__start(s), up=False)
            return [(start, finish)]
        else:
            return []

    def __missing_recent(self, s, response, now):
        finish = s.query(StatisticJournal.time). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.name == response,
                   StatisticName.owner == self.owner_out). \
            order_by(StatisticJournal.time.desc()).limit(1).one_or_none()
        if finish is None:
            log.debug(f'Missing data for {response}')
            return True
        if (now - finish[0]).total_seconds() > 3 * 60 * 60:
            log.debug(f'Insufficient data for {response}')
            return True
        return False

    def __missing_sources(self, s):
        response_ids = s.query(StatisticName.id). \
            filter(StatisticName.owner == self.owner_out)
        inputs = s.query(CompositeComponent.input_source_id). \
            join(StatisticJournal, StatisticJournal.source_id == CompositeComponent.output_source_id). \
            filter(StatisticJournal.statistic_name_id.in_(response_ids),
                   CompositeComponent.input_source_id != None)
        unused = s.query(count(StatisticJournal.id)). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.name == HR_IMPULSE_10,
                   StatisticName.owner == self.owner_in,
                   ~StatisticJournal.source_id.in_(inputs))
        log.debug(unused)
        log.debug(f'owner_in: {self.owner_in}')
        log.debug(f'owner_out: {self.owner_out}')
        return unused.scalar()

    def __start(self, s):
        # avoid constants defined at time 0
        return s.query(StatisticJournal.time). \
            filter(StatisticJournal.time > 1.0). \
            order_by(StatisticJournal.time.asc()). \
            limit(1).scalar()

    def _run_one(self, s, missed):
        hr10 = statistics(s, HR_IMPULSE_10, constraint=ActivityGroup.from_name(s, ALL),
                          owner=self.owner_in, with_sources=True, check=False)
        if not hr10.empty:
            hr10.loc[now()] = {HR_IMPULSE_10: 0.0, _src(HR_IMPULSE_10): None}
            all_sources = list(self.__make_sources(s, hr10))
            for response in self.responses:
                log.info(f'Creating values for {response.dest_name}')
                hr3600 = sum_to_hour(hr10, HR_IMPULSE_10)
                params = (log10(response.tau_days * 24),
                          log10(response.start) if response.start > 0 else 1)
                result = calc_response(hr3600, params) * response.scale
                loader = self._get_loader(s, add_serial=False)
                source, sources = None, list(all_sources)
                for time, value in result.iteritems():
                    while sources and time >= sources[0][0]:
                        source = sources.pop(0)[1]
                    loader.add(response.dest_name, None, None, None, source, value, time, StatisticJournalFloat)
                loader.load()

    def __make_sources(self, s, hr10):
        log.info('Creating sources')
        name = _src(HR_IMPULSE_10)
        prev = add(s, Composite(n_components=0))
        yield to_time(0.0), prev
        # find times where the source changes
        for time, row in hr10.loc[hr10[name].ne(hr10[name].shift())].iterrows():
            id = row[name]
            if id:
                composite = add(s, Composite(n_components=2))
                add(s, CompositeComponent(input_source_id=id, output_source=composite))
            else:
                composite = add(s, Composite(n_components=1))
            add(s, CompositeComponent(input_source=prev, output_source=composite))
            yield time, composite
            prev = composite
        s.commit()
