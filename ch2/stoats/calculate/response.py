
from collections import namedtuple
from json import loads
from logging import getLogger
from math import log10
import datetime as dt

from sqlalchemy.sql.functions import count

from . import UniProcCalculator
from ...data.frame import statistics
from ...data.response import pre_calc, DecayModel, calc
from ...lib.date import round_hour, to_time, local_date_to_time
from ...squeal import ActivityGroup
from ...squeal import StatisticJournal, Composite, StatisticName, Source, Constant, CompositeComponent, \
    StatisticJournalFloat
from ...squeal.utils import add
from ...stoats.names import _src, ALL, HR_IMPULSE_10
from ...stoats.pipeline import LoaderMixin

log = getLogger(__name__)

Response = namedtuple('Response', 'src_owner, dest_name, tau_days, scale, start')


class ResponseCalculator(LoaderMixin, UniProcCalculator):
    '''
    this is hard to do correctly, incrementally.

    for now, we do all or nothing.

    first, we check if the current solution is complete:
    * all sources used (no need to check for gaps - composite chaining should do that)
    * within 3 hours of the current time (if not, we regenerate, padding with zeroes)

    if not complete, we regenerate the whole damn thing.
    '''

    def __init__(self, *args, responses_ref=None, impulse_ref=None, **kargs):
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
            filter(StatisticJournal.statistic_name_id.in_(response_ids))
        unused = s.query(count(StatisticJournal.id)). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.name == HR_IMPULSE_10,
                   StatisticName.owner == self.owner_in,
                   ~StatisticJournal.source_id.in_(inputs)).scalar()
        return unused

    def __start(self, s):
        # avoid constants defined at time 0
        return s.query(StatisticJournal.time). \
            filter(StatisticJournal.time > 1.0). \
            order_by(StatisticJournal.time.asc()). \
            limit(1).scalar()

    def _run_one(self, s, missed):
        start, finish = missed
        hr10 = statistics(s, HR_IMPULSE_10, constraint=ActivityGroup.from_name(s, ALL),
                          owner=self.owner_in, with_sources=True, check=False)
        if not hr10.empty:
            all_sources = list(self.__make_sources(s, hr10))
            for response in self.responses:
                log.info(f'Creating values for {response.dest_name}')
                model = DecayModel(start=response.start, zero=0, log10_scale=log10(response.scale),
                                   log10_period=log10(response.tau_days * 24 * 60 * 60 / 3600),  # convert to intervals
                                   input=HR_IMPULSE_10, output=response.dest_name)
                hr3600 = pre_calc(hr10.copy(), model, start=start, finish=finish)
                result = calc(hr3600, model)
                loader = self._get_loader(s, add_serial=False)
                source, sources = None, list(all_sources)
                for time, row in result.iterrows():
                    while sources and time >= sources[0][0]:
                        source = sources.pop(0)[1]
                    loader.add(response.dest_name, None, None, None, source, row[response.dest_name], time,
                               StatisticJournalFloat)
                loader.load()

    def __make_sources(self, s, hr10):
        log.info('Creating sources')
        name = _src(HR_IMPULSE_10)
        prev = add(s, Composite(n_components=0))
        yield to_time(0.0), prev
        # find times where the source changes
        for time, row in hr10.loc[hr10[name].ne(hr10[name].shift())].iterrows():
            id = row[name]
            composite = add(s, Composite(n_components=2))
            add(s, CompositeComponent(input_source_id=id, output_source=composite))
            add(s, CompositeComponent(input_source=prev, output_source=composite))
            yield time, composite
            prev = composite
        s.commit()
