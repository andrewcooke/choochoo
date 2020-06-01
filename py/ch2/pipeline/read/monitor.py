
import datetime as dt
from collections import defaultdict
from logging import getLogger

import numpy as np
from sqlalchemy import desc, and_, or_, func
from sqlalchemy.sql.functions import count

from .utils import AbortImport, AbortImportButMarkScanned, MultiProcFitReader
from ..loader import StatisticJournalLoader
from ...commands.args import mm, FORCE, READ
from ...data.frame import read_query
from ...fit.format.records import fix_degrees, unpack_single_bytes, merge_duplicates
from ...fit.profile.profile import read_fit
from ...lib.date import time_to_local_date, format_time
from ...names import N, T, Units
from ...sql.database import StatisticJournalType
from ...sql.tables.monitor import MonitorJournal
from ...sql.tables.statistic import StatisticJournalInteger, StatisticName, StatisticJournal
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


class MonitorLoader(StatisticJournalLoader):

    def _preload(self):
        dummy = super()._preload()
        try:
            for name in self._s.query(StatisticName). \
                    filter(StatisticName.name == N.CUMULATIVE_STEPS,
                           StatisticName.owner == self._owner).all():
                n = self._s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.statistic_name == name,
                           StatisticJournal.time >= self.start,
                           StatisticJournal.time <= self.finish).scalar()
                if n and self.start and self.finish:
                    log.debug(f'Deleting {n} overlapping {N.CUMULATIVE_STEPS}')
                    self._s.query(StatisticJournal). \
                        filter(StatisticJournal.statistic_name == name,
                               StatisticJournal.time >= self.start,
                               StatisticJournal.time <= self.finish).delete()
        except:
            log.warning('Failed to clean database')
            self._s.rollback()
            raise
        return dummy

    def _resolve_duplicate(self, name, instance, prev):
        log.warning(f'Using max of duplicate values at {instance.time} for {name} ({instance.value}/{prev.value})')
        prev.value = max(prev.value, instance.value)


NEW_STEPS = N._new(N.STEPS)
STEPS_DESCRIPTION = '''The increment in steps read from the FIT file.'''


class MonitorReader(MultiProcFitReader):

    def __init__(self, *args, **kargs):
        from ...commands.read import MONITOR
        super().__init__(*args, sub_dir=MONITOR, **kargs)

    def _get_loader(self, s, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        return MonitorLoader(s, **kargs)

    def _base_command(self):
        force = mm(FORCE) if self.force else ""
        return f'{READ} {force}'

    def _delete_contained(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start >= start,
                       MonitorJournal.finish <= finish).all():
            log.warning(f'Replacing data from {mjournal.start} to {mjournal.finish} with data from '
                        f'{path} ({start} - {finish}')
            s.delete(mjournal)

    def _check_inside(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(or_(and_(MonitorJournal.start <= start, MonitorJournal.finish > finish),
                           and_(MonitorJournal.start < start, MonitorJournal.finish >= finish))).all():
            log.warning('%s already includes data from %s for %s - %s' % (mjournal, path, start, finish))
            raise AbortImportButMarkScanned()

    def _check_overlap(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(or_(and_(MonitorJournal.start < start,
                                MonitorJournal.finish > start, MonitorJournal.finish < finish),
                           and_(MonitorJournal.finish > finish,
                                MonitorJournal.start > start, MonitorJournal.start < finish))).all():
            log.warning('%s overlaps data from %s for %s - %s' % (mjournal, path, start, finish))
            raise AbortImport()

    def _delete_previous(self, s, start, finish, path):
        self._check_inside(s, start, finish, path)
        self._check_overlap(s, start, finish, path)
        self._delete_contained(s, start, finish, path)
        s.commit()

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
            log.debug('File %s is empty (no timespan)' % file_scan)
            raise AbortImportButMarkScanned()
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % file_scan)

        log.info(f'Importing monitor data from {file_scan} '
                 f'for {format_time(first_timestamp)} - {format_time(last_timestamp)}')
        self._delete_previous(s, first_timestamp, last_timestamp, file_scan)
        mjournal = add(s, MonitorJournal(start=first_timestamp, file_hash=file_scan.file_hash,
                                         finish=last_timestamp))

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
                   StatisticName.owner == self.owner_out)
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
        loader = StatisticJournalLoader(s, owner=self.owner_out)
        for time, row in df.loc[(df[NEW_STEPS] != df[N.STEPS]) & ~df[NEW_STEPS].isna()].iterrows():
            loader.add(T.STEPS, Units.STEPS_UNITS, None, row[N.SOURCE], int(row[NEW_STEPS]),
                       time, StatisticJournalInteger, description=STEPS_DESCRIPTION)
        loader.load()
