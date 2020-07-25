import datetime as dt
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np
from math import log10
from sqlalchemy import distinct
from sqlalchemy.sql.functions import count

from .utils import ProcessCalculator
from ..pipeline import LoaderMixin, OwnerInMixin
from ..read.segment import SegmentReader
from ...common.date import round_hour, to_time, local_date_to_time, now, format_time
from ...common.names import TIME_ZERO
from ...data import Statistics, present
from ...data.response import sum_to_hour, calc_response
from ...names import Names as N, SPACE
from ...sql import StatisticJournal, Composite, StatisticName, Source, Constant, CompositeComponent, \
    StatisticJournalFloat
from ...sql.tables.source import SourceType
from ...sql.utils import add

log = getLogger(__name__)

Response = namedtuple('Response', 'src_owner, title, tau_days, start, scale')

SCALED = 'scaled'


class ResponseCalculator(LoaderMixin, OwnerInMixin, ProcessCalculator):
    '''
    this is hard to do correctly, incrementally.

    for now, we do all or nothing.

    first, we check if the current solution is complete:
    * all sources used (no need to check for gaps - composite chaining should do that)
    * within 3 hours of the current time (if not, we regenerate, padding with zeroes)

    if not complete, we regenerate the whole damn thing.
    '''

    def __init__(self, *args, response_constants=None, prefix=None, **kargs):
        self.response_constant_names = self._assert('response_constants', response_constants)
        self.prefix = self._assert('prefix', prefix)
        super().__init__(*args, **kargs)

    def startup(self):
        with self._config.db.session_context(expire_on_commit=False) as s:
            self.response_constants = [Constant.from_name(s, name) for name in self.response_constant_names]
            self.responses = [Response(**loads(constant.at(s).value)) for constant in self.response_constants]
        super().startup()

    def _delete(self, s):
        composite_ids = s.query(Composite.id). \
            join(StatisticJournal, Composite.id == StatisticJournal.source_id). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.owner == self.owner_out)
        log.debug(f'Delete query: {composite_ids}')
        n = s.query(count(Source.id)). \
            filter(Source.id.in_(composite_ids)). \
            scalar()
        if n:
            log.warning(f'Deleting {n} Composite sources ({start} onwards)')
            s.query(Source). \
                filter(Source.id.in_(composite_ids)). \
                delete(synchronize_session=False)
            s.commit()
            Composite.clean(s)

    def _missing(self, s):
        # clean out any gaps by unzipping the chained composites
        Composite.clean(s)
        # range we expect data for
        finish = round_hour(dt.datetime.now(tz=dt.timezone.utc), up=True)
        missing_sources = self.__missing_sources(s)
        missing_recent = any(self.__missing_recent(s, constant.short_name, finish)
                             for constant in self.response_constants)
        if missing_recent or missing_sources:
            if missing_recent: log.info('Incomplete coverage (so will re-calculate)')
            if missing_sources: log.info('Additional sources (so will re-calculate)')
            self._delete(s)
            start = round_hour(self.__start(s), up=False)
            return [format_time(start)]
        else:
            return []

    def __missing_recent(self, s, constant, now):
        log.debug('Searching for missing recent')
        finish = s.query(StatisticJournal.time). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.name == self.prefix + SPACE + constant,
                   StatisticName.owner == self.owner_out). \
            order_by(StatisticJournal.time.desc()).limit(1).one_or_none()
        if finish is None:
            log.debug(f'Missing data for {constant}')
            return True
        if (now - finish[0]).total_seconds() > 3 * 60 * 60:
            log.debug(f'Insufficient data for {constant}')
            return True
        return False

    def __missing_sources(self, s):
        log.debug('Searching for missing sources')
        available = s.query(count(distinct(Source.id))). \
            join(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == self.prefix + SPACE + N.HR_IMPULSE_10)
        used = s.query(count(distinct(Source.id))). \
            join(CompositeComponent, CompositeComponent.input_source_id == Source.id). \
            join(Composite, Composite.id == CompositeComponent.output_source_id). \
            join(StatisticJournal, StatisticJournal.source_id == Composite.id). \
            join(StatisticName). \
            filter(StatisticName.owner == self.owner_out,
                   Source.type == SourceType.ACTIVITY)
        n_avaialble = available.scalar()
        n_used = used.scalar()
        log.debug(f'Using {n_used} of {n_avaialble} sources')
        return n_used != n_avaialble

    def __start(self, s):
        # avoid constants defined at time 0
        return s.query(StatisticJournal.time). \
            filter(StatisticJournal.time > TIME_ZERO). \
            order_by(StatisticJournal.time.asc()). \
            limit(1).one()[0]  # scalar can return None

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            data = self.__read_data(s)
            if N.HR_IMPULSE_10 in data.columns and N.COVERAGE in data.columns:
                # coverage is calculated by the loader and seems to reflect records that have location data but not
                # HR data.  so i guess it makes sense to scale.
                # i don't remember why / when i added this - it might have been when using an optical monitor?
                # it seems like a relatively small effect in most cases.
                data.loc[now()] = {N.HR_IMPULSE_10: 0.0, N._src(N.HR_IMPULSE_10): None, N.COVERAGE: 100}
                data[SCALED] = data[N.HR_IMPULSE_10] * 100 / data[N.COVERAGE]
                all_sources = list(self.__make_sources(s, data))
                for constant, response in zip(self.response_constants, self.responses):
                    name = self.prefix + SPACE + constant.short_name
                    log.info(f'Creating values for {response.title} ({name})')
                    hr3600 = sum_to_hour(data, SCALED)
                    params = (log10(response.tau_days * 24),
                              log10(response.start) if response.start > 0 else 1)
                    result = calc_response(hr3600, params) * response.scale
                    loader = self._get_loader(s, add_serial=False)
                    source, sources = None, list(all_sources)
                    for time, value in result.iteritems():
                        # the sources are much more spread out than the response, which is calculated every hour so
                        # that it is smooth.  so we only increment the source when necessary.
                        skipped = 0
                        while sources and time >= sources[0][0]:
                            source = sources.pop(0)[1]
                            skipped += 1
                            if skipped > 1:
                                log.warning(f'Skipping multiple sources at {time}')
                        loader.add(name, None, None, source, value, time,
                                   StatisticJournalFloat, title=response.title,
                                   description=f'The SHRIMP response for a decay of {response.tau_days} days')
                    loader.load()

    def __read_data(self, s):
        from ..owners import ImpulseCalculator
        name = self.prefix + SPACE + N.HR_IMPULSE_10
        df = Statistics(s, with_source=True).by_name(ImpulseCalculator, name).with_. \
            rename({name: N.HR_IMPULSE_10, N._src(name): N._src(N.HR_IMPULSE_10)}).df
        name = N._cov(N.HEART_RATE)
        df = Statistics(s).by_name(SegmentReader, name).with_. \
            rename({name: N.COVERAGE}).into(df, tolerance='10s')
        if present(df, N.COVERAGE):
            df[N.COVERAGE].fillna(axis='index', method='ffill', inplace=True)
            df[N.COVERAGE].fillna(100, axis='index', inplace=True)
        return df

    def __make_sources(self, s, data):
        # this chains forwards from zero, adding a new composite for each new impulse source.
        # in theory we could reconstruct only missing entries.
        log.info('Creating sources')
        name = N._src(N.HR_IMPULSE_10)
        prev = add(s, Composite(n_components=0))
        yield to_time(0.0), prev
        # find times where the source changes
        changes = data.loc[data[name].ne(data[name].shift())]
        for time, row in changes.iterrows():
            id = row[name]
            if not np.isnan(id):
                composite = add(s, Composite(n_components=2))
                add(s, CompositeComponent(input_source_id=id, output_source=composite))
            else:
                composite = add(s, Composite(n_components=1))
            add(s, CompositeComponent(input_source=prev, output_source=composite))
            yield time, composite
            prev = composite
        s.commit()
