
from collections import namedtuple
from json import loads
from logging import getLogger

from sqlalchemy.sql.functions import count

from . import UniProcCalculator, DataFrameCalculatorMixin
from ..load import StatisticJournalLoader
from ...data.frame import statistics
from ...data.impulse import pre_calc, DecayModel, calc
from ...lib.date import round_hour, to_time, local_date_to_time
from ...squeal import StatisticJournal, Composite, StatisticName, Source, Constant, CompositeComponent, \
    StatisticJournalFloat
from ...squeal.utils import add
from ...stoats.calculate.heart_rate import HRImpulse
from ...stoats.names import _src

log = getLogger(__name__)

Response = namedtuple('Response', 'src_name, src_owner, dest_name, tau_days, scale, start')


class ImpulseCalculator(DataFrameCalculatorMixin, UniProcCalculator):
    '''
    this is hard to do correctly, incrementally.

    for now, we do all or nothing.

    first, we check if the current solution is complete:
    * extends across full date range
    * all sources used
    (no need to check for gaps - composite chaining should do that)

    if not complete, we regenerate the whole damn thing.
    '''

    def __init__(self, *args, responses=None, impulse=None, **kargs):
        self.responses_ref = self._assert('responses', responses)
        self.impulse_ref = self._assert('impulse', impulse)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self.constants = [Constant.get(s, response) for response in self.responses_ref]
        self.responses = [Response(**loads(constant.at(s).value)) for constant in self.constants]
        self.impulse = HRImpulse(**loads(Constant.get(s, self.impulse_ref).at(s).value))

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
        start = round_hour(self.__full_range(s, True), up=False)
        finish = round_hour(self.__full_range(s, False), up=True)
        n_secs = (finish - start).total_seconds()
        missing_coverage = any(self.__missing_coverage(s, response.dest_name, n_secs) for response in self.responses)
        missing_sources = self.__missing_sources(s)
        if missing_coverage or missing_sources:
            if missing_coverage: log.info('Incomplete coverage (so will re-calculate)')
            if missing_sources: log.info('Additional sources (so will re-calculate)')
            self._delete_from(s)
            return [(start, finish)]
        else:
            return []

    def __missing_coverage(self, s, response, n_secs):
        q = s.query(StatisticJournal.time). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.name == response,
                   StatisticName.owner == self.owner_out)
        start = q.order_by(StatisticJournal.time.asc()).limit(1).one_or_none()
        finish = q.order_by(StatisticJournal.time.desc()).limit(1).one_or_none()
        if start is None or finish is None:
            log.debug(f'Missing data for {response}')
            return True
        delta = (finish[0] - start[0]).total_seconds()
        if delta < n_secs:
            log.debug(f'Insufficient data for {response}: {delta}s / {n_secs}s (difference of {n_secs - delta}s)')
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
            filter(StatisticName.name == self.impulse.dest_name,
                   StatisticName.owner == self.owner_in,
                   ~StatisticJournal.source_id.in_(inputs)).scalar()
        return unused

    def __full_range(self, s, start=True):
        q = s.query(StatisticJournal.time). \
            filter(StatisticJournal.time > 1.0)  # avoid constants
        if start:
            q = q.order_by(StatisticJournal.time.asc())
        else:
            q = q.order_by(StatisticJournal.time.desc())
        return q.limit(1).scalar()

    def _run_one(self, s, missed):
        start, finish = missed
        hr10 = statistics(s, self.impulse.dest_name, owner=self.owner_in, with_sources=True)
        if not hr10.empty:
            all_sources = list(self.__make_sources(s, hr10))
            for response in self.responses:
                log.info(f'Creating values for {response.dest_name}')
                model = DecayModel(start=response.start, zero=0, scale=response.scale,
                                   period=response.tau_days * 24 * 60 * 60 / 3600,  # convert to intervals
                                   input=self.impulse.dest_name, output=response.dest_name)
                hr3600 = pre_calc(hr10.copy(), model, start=start, finish=finish)
                result = calc(hr3600, model)
                loader = StatisticJournalLoader(s, self.owner_out, add_serial=False)
                source, sources = None, list(all_sources)
                for time, row in result.iterrows():
                    while sources and time >= sources[0][0]:
                        source = sources.pop(0)[1]
                    loader.add(response.dest_name, None, None, None, source, row[response.dest_name], time,
                               StatisticJournalFloat)
                loader.load()

    def __make_sources(self, s, hr10):
        log.info('Creating sources')
        name = _src(self.impulse.dest_name)
        prev = add(s, Composite(n_components=0))
        yield to_time(0.0), prev
        for time, row in hr10.loc[hr10[name].ne(hr10[name].shift())].iterrows():
            id = row[name]
            composite = add(s, Composite(n_components=2))
            add(s, CompositeComponent(input_source_id=id, output_source=composite))
            add(s, CompositeComponent(input_source=prev, output_source=composite))
            yield time, composite
            prev = composite
        s.commit()
