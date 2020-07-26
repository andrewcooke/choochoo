
import datetime as dt
from collections import defaultdict
from logging import getLogger

import numpy as np
from sqlalchemy import desc, and_, func
from sqlalchemy.orm import aliased

from .utils import AbortImportButMarkScanned, ProcessFitReader
from ..loader import Loader
from ..pipeline import LoaderMixin
from ...common.date import time_to_local_date, format_time, to_time, dates_from, now
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
    days = (time_to_local_date(now()) - start).days
    if days > 14 and not force:
        raise Exception('Too many days (%d) - ' % days +
                        'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
    if days:
        yield from dates_from(start)
    else:
        log.warning('No dates to download')


NEW_STEPS = N._new(N.STEPS)
STEPS_DESCRIPTION = '''The increment in steps read from the FIT file.'''


class MonitorReader(LoaderMixin, ProcessFitReader):

    '''
    These overlap (well, often one starts when another ends),
    so we read everything in and then, at the end, remove overlaps.
    '''

    def __init__(self, config, *args, **kargs):
        from ...commands.upload import MONITOR
        super().__init__(config, *args, sub_dir=MONITOR, **kargs)

    def _get_loader(self, s, **kargs):
        return super()._get_loader(s, cls=MonitorLoader, **kargs)

    @staticmethod
    def parse_records(data):
        return MonitorReader.read_fit_file(data, merge_duplicates, fix_degrees, unpack_single_bytes)

    @staticmethod
    def read_first_timestamp(path, records):
        return MonitorReader._first(path, records, MONITORING_INFO_ATTR).value.timestamp

    @staticmethod
    def read_last_timestamp(path, records):
        return MonitorReader._last(path, records, MONITORING_ATTR).value.timestamp

    def _delete(self, s):
        self._delete_n(s, 100)

    def _delete_db(self, s, file_scan):
        q = s.query(MonitorJournal.id).filter(MonitorJournal.file_hash == file_scan.file_hash)
        s.query(Source).filter(Source.id.in_(q)).delete(synchronize_session=False)

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
        if s.query(MonitorJournal).filter(MonitorJournal.file_hash == file_scan.file_hash).count():
            raise Exception(f'Duplicate for {file_scan.path}')  # should never happen
        mjournal = add(s, MonitorJournal(start=first_timestamp, finish=last_timestamp,
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

    def shutdown(self):
        super().shutdown()
        if not self.worker:
            with self._config.db.session_context() as s:
                log.info('Calculating differential in main thread')
                self._fix_overlapping_monitors(s)
                s.commit()
                self._update_differential(s)

    def _fix_overlapping_monitors(self, s):
        # this used to be done in python and was very slow
        self._delete_nested(s)
        self._shift_finish(s)
        self._delete_past_finish(s)

    def _delete_nested(self, s):
        # first, remove any monitor journal entries which are completely enclosed by others
        m1 = aliased(MonitorJournal)
        m2 = aliased(MonitorJournal)
        nested = s.query(m2.id).join(m1). \
            filter(m1.start <= m2.start,
                   m1.finish >= m2.finish,
                   m1.id != m2.id)
        q = s.query(Source).filter(Source.id.in_(nested))
        count = q.count()
        if count:
            log.warning(f'Deleting {count} nested journal entries')
            q.delete()
        else:
            log.debug('No nested journal entries')

    def _shift_finish(self, s):
        # next, fix up overlapping monitor journal entries so that they abut
        log.info(f'Adjusting finish')
        m1 = aliased(MonitorJournal)
        m2 = aliased(MonitorJournal)
        # this is giving a warning but post to sqlalchemy group was deleted
        overlap = s.query(m1.id.label('id'), m2.start.label('finish')). \
            filter(m1.start < m2.start,
                   m1.finish > m2.start,
                   m1.id != m2.id).cte()
        s.query(MonitorJournal). \
            filter(MonitorJournal.id == overlap.c.id). \
            update({MonitorJournal.finish: overlap.c.finish})

    def _delete_past_finish(self, s):
        # finally, drop any values that are not included in the shortened journals
        q = s.query(StatisticJournal.id). \
            join(MonitorJournal). \
            filter(StatisticJournal.source_id == MonitorJournal.id,
                   StatisticJournal.time >= MonitorJournal.finish)
        count = q.count()
        if count:
            log.warning(f'Deleting {count} orphan statistics')
            # dance around the inability to call q.delete() directly
            s.query(StatisticJournal).filter(StatisticJournal.id.in_(q)).delete(synchronize_session=False)
        else:
            log.debug('No orphan statistics')

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
            times = [to_time(time) for time in times]
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


class MonitorLoader(Loader):

    def _resolve_duplicate(self, name, instance, prev):
        log.warning(f'Using max of duplicate values at {instance.time} for {name} '
                    f'({instance.value}/{prev.value})')
        prev.value = max(prev.value, instance.value)
