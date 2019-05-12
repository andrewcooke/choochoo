
import datetime as dt
from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import desc, and_, or_, distinct, func, select
from sqlalchemy.sql.functions import count

from ..load import StatisticJournalLoader
from ..names import HEART_RATE, BPM, STEPS, STEPS_UNITS, CUMULATIVE_STEPS, _new, TIME, SOURCE
from ..read import AbortImportButMarkScanned, AbortImport, MultiProcFitReader
from ...commands.args import MONITOR, WORKER, FAST, mm, FORCE
from ...data.frame import _tables
from ...fit.format.records import fix_degrees, unpack_single_bytes, merge_duplicates
from ...lib.date import time_to_local_date, format_time
from ...squeal.database import StatisticJournalType
from ...squeal.tables.monitor import MonitorJournal
from ...squeal.tables.statistic import StatisticJournalInteger, StatisticName, StatisticJournal
from ...squeal.utils import add

log = getLogger(__name__)
ACTIVITY_TYPE_ATTR = 'activity_type'
HEART_RATE_ATTR = 'heart_rate'
MONITORING_ATTR = 'monitoring'
MONITORING_INFO_ATTR = 'monitoring_info'
STEPS_ATTR = 'steps'


def missing_dates(s):
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
    start = time_to_local_date(latest.start + dt.timedelta(seconds=seconds) + dt.timedelta(days=1))
    finish = dt.date.today()
    days = (finish - start).days
    if days > 14:
        raise Exception('Too many days (%d) - ' % days +
                        'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
    if days:
        # exclude today since it will be incomplete
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
                    filter(StatisticName.name == CUMULATIVE_STEPS,
                           StatisticName.owner == self._owner).all():
                n = self._s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.statistic_name == name,
                           StatisticJournal.time >= self.start,
                           StatisticJournal.time <= self.finish).scalar()
                if n and self.start and self.finish:
                    log.warning(f'Deleting {n} overlapping {CUMULATIVE_STEPS}')
                    self._s.query(StatisticJournal). \
                        filter(StatisticJournal.statistic_name == name,
                               StatisticJournal.time >= self.start,
                               StatisticJournal.time <= self.finish).delete()
        except:
            log.debug('Failed to clean database')
            self._s.rollback()
            raise
        return dummy

    def _resolve_duplicate(self, name, instance, prev):
        log.warning(f'Using max of duplicate values at {instance.time} for {name} ({instance.value}/{prev.value})')
        prev.value = max(prev.value, instance.value)


NEW_STEPS = _new(STEPS)


class MonitorReader(MultiProcFitReader):

    def _get_loader(self, s, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        return MonitorLoader(s, **kargs)

    def _base_command(self):
        return f'{{ch2}} -v0 -l {{log}} -f {self._db.path} {MONITOR} {mm(WORKER)} {self.id} {mm(FAST)} {mm(FORCE) if self.force else ""}'

    def _delete_contained(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start >= start,
                       MonitorJournal.finish <= finish).all():
            log.warning(f'Replacing {mjournal.fit_file} ({mjournal.start} - {mjournal.finish}) with data from '
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

    def _read_data(self, s, path):

        records = self._read_fit_file(path, merge_duplicates, fix_degrees, unpack_single_bytes)

        first_timestamp = self._first(path, records, MONITORING_INFO_ATTR).timestamp
        last_timestamp = self._last(path, records, MONITORING_ATTR).timestamp
        if first_timestamp == last_timestamp:
            log.debug('File %s is empty (no timespan)' % path)
            raise AbortImportButMarkScanned()
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % path)

        log.info(f'Importing monitor data from {path} '
                 f'for {format_time(first_timestamp)} - {format_time(last_timestamp)}')
        self._delete_previous(s, first_timestamp, last_timestamp, path)
        mjournal = add(s, MonitorJournal(start=first_timestamp, fit_file=path, finish=last_timestamp))

        return mjournal.id, (first_timestamp, last_timestamp, mjournal, records)

    def _load_data(self, s, loader, data):
        first_timestamp, last_timestamp, mjournal, records = data
        for record in records:
            if HEART_RATE_ATTR in record.data:
                loader.add(HEART_RATE, BPM, None, None, mjournal, record.data[HEART_RATE_ATTR][0][0],
                           record.timestamp, StatisticJournalInteger)
            if STEPS_ATTR in record.data:
                for (activity, steps) in zip(record.data[ACTIVITY_TYPE_ATTR][0], record.data[STEPS_ATTR][0]):
                    loader.add(CUMULATIVE_STEPS, STEPS_UNITS, None, activity, mjournal, steps,
                               record.timestamp, StatisticJournalInteger)

    def _shutdown(self, s):
        super()._shutdown(s)
        if not self.worker:
            for activity in self._step_activities(s):
                df = self._read_diff(s, activity)
                df = self._calculate_diff(df)
                self._write_diff(s, df, activity)

    def _step_activities(self, s):
        return [row[0] for row in s.query(distinct(StatisticName.constraint)).
            filter(StatisticName.name == CUMULATIVE_STEPS,
                   StatisticName.owner == self.owner_out).all()]

    def _read_diff(self, s, activity):
        t = _tables()
        qs = select([t.sj.c.time.label("time"), t.sji.c.value.label("steps")]). \
            select_from(t.sj.join(t.sn).join(t.sji)). \
            where(and_(t.sn.c.name == STEPS, t.sn.c.constraint == activity,
                       t.sn.c.owner == self.owner_out)).alias("steps")
        q = select([t.sj.c.time.label(TIME), t.sj.c.source_id.label(SOURCE), t.sji.c.value.label(CUMULATIVE_STEPS),
                    qs.c.steps.label(STEPS)]). \
            select_from(t.sj.join(t.sn).join(t.sji).outerjoin(qs, t.sj.c.time == qs.c.time)). \
            where(and_(t.sn.c.name == CUMULATIVE_STEPS, t.sn.c.constraint == activity,
                       t.sn.c.owner == self.owner_out)). \
            order_by(t.sj.c.time)
        # log.debug(q)
        df = pd.read_sql_query(sql=q, con=s.connection(), index_col=TIME)
        return df

    def _calculate_diff(self, df):
        df[NEW_STEPS] = df[CUMULATIVE_STEPS].diff()
        df.loc[df[NEW_STEPS] < 0, NEW_STEPS] = df[CUMULATIVE_STEPS]
        df.loc[df[NEW_STEPS].isna(), NEW_STEPS] = df[CUMULATIVE_STEPS]
        return df

    def _write_diff(self, s, df, activity):
        steps = StatisticName.add_if_missing(log, s, STEPS, StatisticJournalType.INTEGER, STEPS_UNITS, None,
                                             self.owner_out, activity)
        times = df.loc[(df[NEW_STEPS] != df[STEPS]) & ~df[STEPS].isna()].index.astype(np.int64) / 1e9
        if len(times):
            n = s.query(func.count(StatisticJournal.id)). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).scalar()
            log.warning(f'Deleting {n} {STEPS}/{activity} entries')
            s.query(StatisticJournal.id). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).delete(synchronize_session=False)
        loader = StatisticJournalLoader(s, owner=self.owner_out)
        for time, row in df.loc[(df[NEW_STEPS] != df[STEPS]) & ~df[NEW_STEPS].isna()].iterrows():
            loader.add(STEPS, STEPS_UNITS, None, activity, row[SOURCE], int(row[NEW_STEPS]),
                       time, StatisticJournalInteger)
        loader.load()
