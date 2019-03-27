
import datetime as dt
from collections import defaultdict
from logging import getLogger

import pandas as pd
import numpy as np
from cachetools import cached
from sqlalchemy import desc, and_, or_, distinct, func, alias, select

from ..load import StatisticJournalLoader
from ..names import HEART_RATE, BPM, STEPS, STEPS_UNITS, ACTIVITY, CUMULATIVE_STEPS_START, \
    CUMULATIVE_STEPS_FINISH, CUMULATIVE_STEPS, _new, TIME, SOURCE
from ..read import AbortImportButMarkScanned, AbortImport, MultiProcFitReader, UniProcFitReader
from ...commands.args import MONITOR, WORKER, FAST, mm, FORCE
from ...data import statistics
from ...data.frame import _tables
from ...fit.format.records import fix_degrees, unpack_single_bytes, merge_duplicates
from ...lib.date import time_to_local_date, format_time
from ...squeal.database import Timestamp
from ...squeal.tables.monitor import MonitorJournal
from ...squeal.tables.statistic import StatisticJournalInteger, StatisticJournalText, StatisticName, StatisticJournal
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
    if days > 10:
        raise Exception('Too many days (%d) - ' % days +
                        'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
    if days:
        # exclude today since it will be incomplete
        while start < finish:
            yield start
            start += dt.timedelta(days=1)
    else:
        log.warning('No dates to download')


class OldMessMonitorReader(UniProcFitReader):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        @cached(cache={}, key=lambda s, name, units, summary, constraint: (name, constraint))
        def statistics_cache(s, name, units, summary, constraint):
            return StatisticName.add_if_missing(log, s, name, units, summary, self, constraint)

        self.__statistics_cache = statistics_cache

    def _create(self, s, name, units, summary, constraint, source, value, time, type):
        return type(statistic_name=self.__statistics_cache(s, name, units, summary, constraint),
                    source=source, value=value, time=time)

    def _add(self, s, name, units, summary, constraint, source, value, time, type):
        return add(s, self._create(s, name, units, summary, constraint, source, value, time, type))

    def _check_contains(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start >= start,
                       MonitorJournal.finish <= finish).all():
            log.warning('Replacing %s with data from %s for %s - %s' % (mjournal, path, start, finish))
            s.delete(mjournal)

    def _check_inside(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start <= start,
                       MonitorJournal.finish >= finish).all():
            log.warning('%s already includes data from %s for %s - %s' % (mjournal, path, start, finish))
            raise AbortImportButMarkScanned()

    def _check_overlap(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start < finish,
                       MonitorJournal.finish > start).all():
            log.warning('%s overlaps data from %s for %s - %s' % (mjournal, path, start, finish))
            raise AbortImport()

    def _check_previous(self, s, start, finish, path):
        self._check_contains(s, start, finish, path)
        self._check_inside(s, start, finish, path)
        self._check_overlap(s, start, finish, path)

    def _delete_journals(self, s, first_timestamp, path):
        # key only on time so that repeated files don't affect things
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start == first_timestamp).all():
            Timestamp.clear(s, owner=self.owner_out, key=mjournal.id)
            log.debug('Deleting %s' % mjournal)
            s.delete(mjournal)
        s.flush()

    def _delta(self, steps, activity, cumulative):
        if steps >= cumulative[activity]:
            delta = steps - cumulative[activity]
        else:
            delta = steps
        cumulative[activity] = steps
        return delta

    def _save_cumulative(self, s, time, cumulative, mjournal, name):
        log.debug('Adding %s at time %s' % (name, format_time(time)))
        for activity in cumulative:
            self._add(s, name, STEPS_UNITS, None, activity,
                      mjournal, cumulative[activity], time, StatisticJournalInteger)
        log.debug('Added: %s' % ', '.join('%s:%s' % item for item in cumulative.items()))

    def _update_cumulative(self, s, time, cumulative, mjournal, name, saved):
        # go back and fill in with zeroes and missing starting values
        for activity in saved:
            del cumulative[activity]
        if cumulative:
            for activity in cumulative:
                cumulative[activity] = 0
            self._save_cumulative(s, time, cumulative, mjournal, name)

    def _read_cumulative(self, s, time, cumulative, name):
        # no constraint, so all activities
        for journal in s.query(StatisticJournalInteger).join(StatisticName). \
                filter(StatisticJournalInteger.time == time,
                       StatisticName.name == name,
                       StatisticName.owner == self).all():
            cumulative[journal.statistic_name.constraint] = journal.value
        log.debug('Read %s at %s' % (name, format_time(time)))
        log.debug('Read: %s' % ', '.join('%s:%s' % item for item in cumulative.items()))

    def _read_previous(self, s, first_timestamp, cumulative):
        prev = s.query(MonitorJournal). \
            filter(MonitorJournal.finish <= first_timestamp). \
            order_by(desc(MonitorJournal.finish)).limit(1).one_or_none()
        if prev:
            self._read_cumulative(s, prev.finish, cumulative, CUMULATIVE_STEPS_FINISH)

    def _update_next(self, s, last_timestamp, cumulative):
        log.debug('Checking for following file after %s' % format_time(last_timestamp))
        next = s.query(MonitorJournal). \
            filter(MonitorJournal.start >= last_timestamp). \
            order_by(MonitorJournal.start).limit(1).one_or_none()
        if next:
            log.debug('Found file at %s - fixing up' % format_time(next.start))
            # no constraint, so all activities
            for cumulative_journal in s.query(StatisticJournalInteger).join(StatisticName). \
                    filter(StatisticJournalInteger.time == next.start,
                           StatisticName.name == CUMULATIVE_STEPS_START,
                           StatisticName.owner == self).all():
                activity = cumulative_journal.statistic_name.constraint
                if activity in cumulative and cumulative[activity] != cumulative_journal.value:
                    log.debug('Found %s with inconsistent value (%s != %s)' %
                              (CUMULATIVE_STEPS_START, cumulative_journal.value, cumulative[activity]))
                    steps_journal = StatisticJournal.after(s, next.start, STEPS, self, activity)
                    log.debug('Found %s with value %s' % (STEPS, steps_journal.value))
                    # only fix up if the cumulative value didn't reset
                    if steps_journal.value + cumulative_journal.value >= cumulative[activity]:
                        steps_journal.value = steps_journal.value - cumulative[activity] + cumulative_journal.value
                        log.debug('Updated %s at %s to %s' %
                                  (STEPS, format_time(last_timestamp), steps_journal.value))
                        cumulative_journal.value = cumulative[activity]
                        if steps_journal.value == 0:
                            activity_journal = StatisticJournal.at(s, steps_journal.time, ACTIVITY, self, activity)
                            s.delete(steps_journal)
                            s.delete(activity_journal)
                            log.debug('Deleted %s and %s' % (STEPS, ACTIVITY))

    def _create_journals(self, s, records, cumulative, mjournal):
        n_heart_rate, n_steps, steps_journals = 0, 0, defaultdict(lambda: {})
        for record in records:
            if HEART_RATE_ATTR in record.data:
                self._add(s, HEART_RATE, BPM, None, None, mjournal, record.data[HEART_RATE_ATTR][0][0],
                          record.timestamp, StatisticJournalInteger)
                n_heart_rate += 1
            if STEPS_ATTR in record.data:
                for (activity, steps) in zip(record.data[ACTIVITY_TYPE_ATTR][0], record.data[STEPS_ATTR][0]):
                    steps = self._delta(steps, activity, cumulative)
                    if steps:
                        if activity in steps_journals[record.timestamp]:
                            # sometimes get values at exactly the same time :(
                            steps_journals[record.timestamp][activity].value += steps
                        else:
                            steps_journals[record.timestamp][activity] = \
                                self._create(s, STEPS, STEPS_UNITS, None, activity,
                                             mjournal, steps, record.timestamp,
                                             StatisticJournalInteger)
                        n_steps += 1
        log.debug('Found %d steps and %d heart rate values' % (n_heart_rate, n_steps))
        return steps_journals

    def _merge_boundary(self, s, steps_journals, time):
        if time in steps_journals:
            for activity in list(steps_journals[time].keys()):
                sjournal = StatisticJournal.at(s, time, STEPS, self, activity)
                if sjournal:
                    if sjournal.value == steps_journals[time][activity].value:
                        log.debug('Matching data at %s' % format_time(time))
                    else:
                        # we have a contradiction, so simply use the latest
                        # could maybe use max() instead?
                        log.warning('Replacing %s data at %s (%s replaced by %s)' %
                                    (STEPS, format_time(time), sjournal.value,
                                     steps_journals[time][activity].value))
                        sjournal.value = steps_journals[time][activity].value
                    del steps_journals[time][activity]

    def _read_data(self, s, path):

        records = self._read_fit_file(path, merge_duplicates, fix_degrees, unpack_single_bytes)

        first_timestamp = self._first(path, records, MONITORING_INFO_ATTR).timestamp
        last_timestamp = self._last(path, records, MONITORING_ATTR).timestamp
        if first_timestamp == last_timestamp:
            log.debug('File %s is empty (no timespan)' % path)
            raise AbortImportButMarkScanned()
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % path)
        self._delete_journals(s, first_timestamp, path)

        log.info(f'Importing monitor data from {path} '
                 f'for {format_time(first_timestamp)} - {format_time(last_timestamp)}')
        self._check_previous(s, first_timestamp, last_timestamp, path)
        mjournal = add(s, MonitorJournal(start=first_timestamp, fit_file=path, finish=last_timestamp))

        return mjournal.id, (first_timestamp, last_timestamp, mjournal, records)

    def _load_data(self, s, loader, data):

        first_timestamp, last_timestamp, mjournal, records = data

        cumulative = defaultdict(lambda: 0)
        self._read_previous(s, first_timestamp, cumulative)
        self._save_cumulative(s, first_timestamp, cumulative, mjournal, CUMULATIVE_STEPS_START)
        saved_activities = list(cumulative.keys())

        steps_journals = self._create_journals(s, records, cumulative, mjournal)

        self._save_cumulative(s, last_timestamp, cumulative, mjournal, CUMULATIVE_STEPS_FINISH)
        self._update_next(s, last_timestamp, cumulative)
        self._update_cumulative(s, first_timestamp, cumulative, mjournal, CUMULATIVE_STEPS_START, saved_activities)

        self._merge_boundary(s, steps_journals, first_timestamp)
        self._merge_boundary(s, steps_journals, last_timestamp)

        # write steps at end, when adjoining data have been fixed
        log.debug('Adding %s to database' % STEPS)
        for timestamp in steps_journals:
            for activity in steps_journals[timestamp]:
                add(s, steps_journals[timestamp][activity])
                self._add(s, ACTIVITY, None, None, activity, mjournal,
                          activity, timestamp, StatisticJournalText)


NEW_STEPS = _new(STEPS)


class MonitorReader(MultiProcFitReader):

    def __init__(self, *args, cost_calc=1, cost_write=1, **kargs):
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _base_command(self):
        return f'{{ch2}} -v0 -l {{log}} {MONITOR} {mm(WORKER)} {self.id} {mm(FAST)} {mm(FORCE) if self.force else ""}'

    def _delete_contained(self, s, start, finish, path):
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.start >= start,
                       MonitorJournal.finish <= finish).all():
            log.warning('Replacing %s with data from %s for %s - %s' % (mjournal, path, start, finish))
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
        steps = StatisticName.add_if_missing(log, s, STEPS, STEPS_UNITS, None, self.owner_out, activity)
        times = df.loc[(df[NEW_STEPS] != df[STEPS]) & ~df[STEPS].isna()].index.astype(np.int64) / 1e9
        if len(times):
            n = s.query(func.count(StatisticJournal.id)).\
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
