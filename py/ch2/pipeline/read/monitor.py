
import datetime as dt
from collections import defaultdict
from logging import getLogger

import numpy as np
from sqlalchemy import desc, and_, func
from sqlalchemy.orm import aliased

import ch2.common.io
from .utils import AbortImportButMarkScanned, MultiProcFitReader
from ..pipeline import LoaderMixin
from ...commands.args import FORCE, READ
from ...common.args import mm
from ...common.date import time_to_local_date, format_time
from ...common.names import POSTGRESQL, SQLITE
from ...data.frame import read_query
from ...fit.format.records import fix_degrees, unpack_single_bytes, merge_duplicates
from ...fit.profile.profile import read_fit
from ...names import N, T, Units
from ...sql import MonitorJournal, StatisticJournalInteger, StatisticName, StatisticJournal
from ...sql.database import StatisticJournalType, Source
from ...sql.utils import add

log = getLogger(__name__)

ACTIVITY_TYPE_ATTR = 'activity_type'
HEART_RATE_ATTR = 'heart_rate'
MONITORING_ATTR = 'monitoring'
MONITORING_INFO_ATTR = 'monitoring_info'
STEPS_ATTR = 'steps'


def missing_dates(s, force=False):
    # we don't try to be perfect here.  the idea is that it's called to get the latest
    # updates, rather than fill in all gaps (do the bulk download thing for that).
    # we also don't try to get fractional data.
    # and as for timezones... we just assume garmin uses the local timezone.
    latest = s.query(MonitorJournal).order_by(desc(MonitorJournal.start)).limit(1).one_or_none()
    if latest is None:
        log.warning('No existing monitor data - ' +
                    'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
        return
    # find the mid-point to avoid any problems with timezones and edge cases
    # (these files don't span more than a day)
    seconds = (latest.finish - latest.start).total_seconds() / 2
    start = time_to_local_date(latest.start + dt.timedelta(seconds=seconds))
    finish = dt.date.today()
    days = (finish - start).days
    if days > 14 and not force:
        raise Exception('Too many days (%d) - ' % days +
                        'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
    if days:
        while start < finish:
            yield start
            start += dt.timedelta(days=1)
    else:
        log.warning('No dates to download')


class MonitorLoaderMixin:

    def _resolve_duplicate(self, name, instance, prev):
        log.warning(f'Using max of duplicate values at {instance.time} for {name} '
                    f'({instance.value}/{prev.value})')
        prev.value = max(prev.value, instance.value)


NEW_STEPS = N._new(N.STEPS)
STEPS_DESCRIPTION = '''The increment in steps read from the FIT file.'''


class MonitorReader(MultiProcFitReader, LoaderMixin):

    '''
    These overlap (well, often one starts when another ends),
    so we read everything in and then, at the end, remove overlaps.
    '''

    def __init__(self, *args, **kargs):
        from ...commands.read import MONITOR
        super().__init__(*args, sub_dir=MONITOR, **kargs)

    def _get_loader(self, s, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        return super()._get_loader(s, **kargs)

    def _base_command(self):
        force = mm(FORCE) if self.force else ""
        return f'{READ} {force}'

    @staticmethod
    def parse_records(data):
        return MonitorReader.read_fit_file(data, merge_duplicates, fix_degrees, unpack_single_bytes)

    @staticmethod
    def read_first_timestamp(path, records):
        return MonitorReader._first(path, records, MONITORING_INFO_ATTR).value.timestamp

    @staticmethod
    def read_last_timestamp(path, records):
        return MonitorReader._last(path, records, MONITORING_ATTR).value.timestamp

    def _read_data(self, s, file_scan):
        records = self.parse_records(read_fit(file_scan.path))
        first_timestamp = self.read_first_timestamp(file_scan.path, records)
        last_timestamp = self.read_last_timestamp(file_scan.path, records)
        if first_timestamp == last_timestamp:
            log.warning('File %s is empty (no timespan)' % file_scan)
            raise AbortImportButMarkScanned()
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % file_scan)

        log.info(f'Importing monitor data from {file_scan} '
                 f'for {format_time(first_timestamp)} - {format_time(last_timestamp)}')
        if self.force:
            log.debug(f'Deleting previous entry')
            s.query(MonitorJournal).filter(MonitorJournal.file_hash == file_scan.file_hash).delete()
        else:
            if s.query(MonitorJournal).filter(MonitorJournal.file_hash == file_scan.file_hash).count():
                raise Exception(f'Duplicate for {file_scan.path}')  # should never happen
        # adding 0.1s to the end time makes the intervals semi-open which simplifies cleanup later
        mjournal = add(s, MonitorJournal(start=first_timestamp,
                                         finish=last_timestamp + dt.timedelta(seconds=0.1),
                                         file_hash_id=file_scan.file_hash.id))
        return mjournal, (first_timestamp, last_timestamp, mjournal, records)

    def _load_data(self, s, loader, data):
        first_timestamp, last_timestamp, mjournal, records = data
        steps_by_activity = defaultdict(lambda: 0)
        for record in records:
            if HEART_RATE_ATTR in record.data and record.data[HEART_RATE_ATTR][0][0]:
                loader.add(T.HEART_RATE, Units.BPM, None, mjournal,
                           record.data[HEART_RATE_ATTR][0][0], record.timestamp, StatisticJournalInteger,
                           description='''The instantaneous heart rate.''')
            if STEPS_ATTR in record.data:
                # we ignore activity type here (used to store it when activity group and statistic name
                # were mixed together, but never used it anywhere)
                reset = False
                for activity, steps in zip(record.data[ACTIVITY_TYPE_ATTR][0], record.data[STEPS_ATTR][0]):
                    reset = reset or steps < steps_by_activity[activity]
                if reset: steps_by_activity = defaultdict(lambda: 0)
                for activity, steps in zip(record.data[ACTIVITY_TYPE_ATTR][0], record.data[STEPS_ATTR][0]):
                    steps_by_activity[activity] = steps
                total = sum(steps_by_activity.values())
                loader.add(T.CUMULATIVE_STEPS, Units.STEPS_UNITS, None,
                           mjournal, total,
                           record.timestamp, StatisticJournalInteger,
                           description='''The number of steps in a day to this point in time.''')

    def _shutdown(self, s):
        super()._shutdown(s)
        if not self.worker:
            log.info('Calculating differential in main thread')
            self._fix_overlapping_monitors(s)
            self._update_differential(s)

    def _fix_overlapping_monitors(self, s):
        pair = self._next_overlap(s)
        while pair:
            self._fix_pair(s, *pair)
            pair = self._next_overlap(s)
        s.commit()

    def _fix_pair(self, s, a, b):
        # a starts before b (from query)
        if b.finish <= a.finish:
            # b completely enclosed in a
            log.warning(f'Deleting monitor journal entry that completely overlaps another')
            log.debug(f'{a.start} - {a.finish} ({a.id}) encloses {b.start} - {b.finish} ({b.id})')
            # be careful to delete superclass...
            s.query(Source).filter(Source.id == b.id).delete()
        else:
            # otherwise, shorten a so it finishes where b starts
            q = s.query(StatisticJournal). \
                filter(StatisticJournal.source == a,
                       StatisticJournal.time >= b.start)
            count = q.count()
            if count:
                # not really a warning because we expect this
                log.debug(f'Shifting edge of overlapping monitor journals ({count} statistic values)')
                log.debug(f'{a.start} - {a.finish} ({a.id}) overlaps {b.start} - {b.finish} ({b.id})')
                q.delete()
            # update monitor whether statistics were changed or not
            log.debug(f'Shift monitor finish back from {a.finish} to {b.start}')
            a.finish = b.start
            s.flush()  # not sure this is needed

    def _next_overlap(self, s):
        MonitorJournal2 = aliased(MonitorJournal)
        row = s.query(MonitorJournal, MonitorJournal2). \
                  select_from(MonitorJournal). \
                  join(MonitorJournal2,
                       # two overlaps, order, and not self and not null
                       and_(MonitorJournal2.finish >= MonitorJournal.start,
                            MonitorJournal2.start < MonitorJournal.finish,
                            MonitorJournal.start <= MonitorJournal2.start,
                            MonitorJournal.id != MonitorJournal2.id)). \
                  order_by(MonitorJournal.start).first()
        return row

    def _update_differential(self, s):
        # this reads CUMULATIVE_STEPS (which is what was in the files) and any existing STEPS
        # then calculates what STEPS should be and fixes up any incorrect or missing data
        # (i guess maybe slightly faster when running incrementally)
        df = self._read_diff(s)
        df = self._calculate_diff(df)
        self._write_diff(s, df)

    def _read_diff(self, s):
        qs = s.query(StatisticJournalInteger.time.label(N.TIME),
                     StatisticJournalInteger.value.label(N.STEPS)). \
            join(StatisticName). \
            filter(StatisticName.name == N.STEPS,
                   StatisticName.owner == self.owner_out).cte()
        q = s.query(StatisticJournalInteger.time.label(N.TIME),
                    StatisticJournalInteger.source_id.label(N.SOURCE),
                    StatisticJournalInteger.value.label(N.CUMULATIVE_STEPS),
                    qs.c.steps.label(N.STEPS)). \
            join(StatisticName).outerjoin(qs, StatisticJournalInteger.time == qs.c.time). \
            filter(StatisticName.name == N.CUMULATIVE_STEPS,
                   StatisticName.owner == self.owner_out). \
            order_by(StatisticJournalInteger.time)
        # log.debug(q)
        df = read_query(q, index=N.TIME)
        return df

    def _calculate_diff(self, df):
        df[NEW_STEPS] = df[N.CUMULATIVE_STEPS].diff()
        df.loc[df[NEW_STEPS] < 0, NEW_STEPS] = df[N.CUMULATIVE_STEPS]
        df.loc[df[NEW_STEPS].isna(), NEW_STEPS] = df[N.CUMULATIVE_STEPS]
        return df

    def _write_diff(self, s, df):
        steps = StatisticName.add_if_missing(s, T.STEPS, StatisticJournalType.INTEGER, Units.STEPS_UNITS,
                                             None, self.owner_out, description=STEPS_DESCRIPTION)
        times = df.loc[(df[NEW_STEPS] != df[N.STEPS]) & ~df[N.STEPS].isna()].index.astype(np.int64) / 1e9
        if len(times):
            n = s.query(func.count(StatisticJournal.id)). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).scalar()
            log.warning(f'Deleting {n} {N.STEPS} entries')
            s.query(StatisticJournal.id). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).delete(synchronize_session=False)
        loader = self._get_loader(s, owner=self.owner_out, add_serial=False)
        for time, row in df.loc[(df[NEW_STEPS] != df[N.STEPS]) & ~df[NEW_STEPS].isna()].iterrows():
            loader.add(T.STEPS, Units.STEPS_UNITS, None, row[N.SOURCE], int(row[NEW_STEPS]),
                       time, StatisticJournalInteger, description=STEPS_DESCRIPTION)
        loader.load()
