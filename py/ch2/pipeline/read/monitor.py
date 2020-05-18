
import datetime as dt
from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import desc, and_, or_, distinct, func, select
from sqlalchemy.sql.functions import count

from .utils import AbortImport, AbortImportButMarkScanned, MultiProcFitReader
from ..loader import StatisticJournalLoader
from ... import FatalException
from ...commands.args import MONITOR, mm, FORCE, DEFAULT
from ...data.frame import _tables
from ...fit.format.records import fix_degrees, unpack_single_bytes, merge_duplicates
from ...fit.profile.profile import read_fit
from ...lib.date import time_to_local_date, format_time
from ...names import Names, Titles, Units
from ...sql.database import StatisticJournalType, ActivityGroup
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
                    filter(StatisticName.name == Names.CUMULATIVE_STEPS,
                           StatisticName.owner == self._owner).all():
                n = self._s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.statistic_name == name,
                           StatisticJournal.time >= self.start,
                           StatisticJournal.time <= self.finish).scalar()
                if n and self.start and self.finish:
                    log.debug(f'Deleting {n} overlapping {Names.CUMULATIVE_STEPS}')
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


NEW_STEPS = Names._new(Names.STEPS)
STEPS_DESCRIPTION = '''The increment in steps read from the FIT file.'''


class MonitorReader(MultiProcFitReader):

    # todo - steps disabled

    def __init__(self, *args, sport_to_activity=None, **kargs):
        from ...commands.upload import MONITOR
        self.sport_to_activity = self._assert('sport_to_activity', sport_to_activity)
        super().__init__(*args, sub_dir=MONITOR, **kargs)

    def _startup(self, s):
        self.sport_to_activity_group = {label: group for label, group in self._expand_activity_groups(s)}
        super()._startup(s)

    def _expand_activity_groups(self, s):
        # extract default values from config that supports more complex activity loading
        for key, value in self.sport_to_activity.items():
            while value and not isinstance(value, str):
                try:
                    value = value[DEFAULT]
                except KeyError:
                    log.warning(f'Missing default in sport_to_activity for {key}')
                    value = None
            if value:
                yield key, ActivityGroup.from_name(s, value)

    def _get_loader(self, s, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        return MonitorLoader(s, **kargs)

    def _base_command(self):
        force = mm(FORCE) if self.force else ""
        return f'{MONITOR} {force}'

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
        mjournal = add(s, MonitorJournal(start=first_timestamp, file_hash=file_scan.file_hash, finish=last_timestamp))

        return mjournal, (first_timestamp, last_timestamp, mjournal, records)

    def _load_data(self, s, loader, data):
        first_timestamp, last_timestamp, mjournal, records = data
        for record in records:
            if HEART_RATE_ATTR in record.data and record.data[HEART_RATE_ATTR][0][0]:
                loader.add(Titles.HEART_RATE, Units.BPM, None, mjournal,
                           record.data[HEART_RATE_ATTR][0][0], record.timestamp, StatisticJournalInteger,
                           description='''The instantaneous heart rate.''')
            # if STEPS_ATTR in record.data:
            #     for (sport, steps) in zip(record.data[ACTIVITY_TYPE_ATTR][0], record.data[STEPS_ATTR][0]):
            #         try:
            #             loader.add(Titles.CUMULATIVE_STEPS, Units.STEPS_UNITS, None,
            #                        mjournal, steps,
            #                        record.timestamp, StatisticJournalInteger,
            #                        description='''The number of steps in a day to this point in time.''')
            #         except KeyError:
            #             raise FatalException(f'There is no group configured for {sport} entries in the FIT file.')

    # def _shutdown(self, s):
    #     super()._shutdown(s)
    #     if not self.worker:
    #         for activity_group_id in self._step_activity_group_ids(s):
    #             df = self._read_diff(s, activity_group_id)
    #             df = self._calculate_diff(df)
    #             self._write_diff(s, df, activity_group_id)

    def _step_activity_group_ids(self, s):
        return [row[0] for row in s.query(distinct(ActivityGroup.id)).
            join(StatisticName).
            filter(StatisticName.name == Names.CUMULATIVE_STEPS,
                   StatisticName.owner == self.owner_out).all()]

    def _read_diff(self, s, activity_group_id):
        t = _tables()
        qs = select([t.sj.c.time.label("time"), t.sji.c.value.label("steps")]). \
            select_from(t.sj.join(t.sn).join(t.sji)). \
            where(and_(t.sn.c.name == Names.STEPS, t.sn.c.activity_group_id == activity_group_id,
                       t.sn.c.owner == self.owner_out)).alias("steps")
        q = select([t.sj.c.time.label(Names.TIME), t.sj.c.source_id.label(Names.SOURCE),
                    t.sji.c.value.label(Names.CUMULATIVE_STEPS),
                    qs.c.steps.label(Names.STEPS)]). \
            select_from(t.sj.join(t.sn).join(t.sji).outerjoin(qs, t.sj.c.time == qs.c.time)). \
            where(and_(t.sn.c.name == Names.CUMULATIVE_STEPS, t.sn.c.activity_group_id == activity_group_id,
                       t.sn.c.owner == self.owner_out)). \
            order_by(t.sj.c.time)
        # log.debug(q)
        df = pd.read_sql_query(sql=q, con=s.connection(), index_col=Names.TIME)
        return df

    def _calculate_diff(self, df):
        df[NEW_STEPS] = df[Names.CUMULATIVE_STEPS].diff()
        df.loc[df[NEW_STEPS] < 0, NEW_STEPS] = df[Names.CUMULATIVE_STEPS]
        df.loc[df[NEW_STEPS].isna(), NEW_STEPS] = df[Names.CUMULATIVE_STEPS]
        return df

    def _write_diff(self, s, df, activity_group_id):
        activity_group = s.query(ActivityGroup).filter(ActivityGroup.id == activity_group_id).one()
        steps = StatisticName.add_if_missing(s, Titles.STEPS, StatisticJournalType.INTEGER, Units.STEPS_UNITS, None,
                                             self.owner_out, activity_group, description=STEPS_DESCRIPTION)
        times = df.loc[(df[NEW_STEPS] != df[Names.STEPS]) & ~df[Names.STEPS].isna()].index.astype(np.int64) / 1e9
        if len(times):
            n = s.query(func.count(StatisticJournal.id)). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).scalar()
            log.warning(f'Deleting {n} {Names.STEPS}/{activity_group} entries')
            s.query(StatisticJournal.id). \
                filter(StatisticJournal.time.in_(times),
                       StatisticJournal.statistic_name == steps).delete(synchronize_session=False)
        loader = StatisticJournalLoader(s, owner=self.owner_out)
        for time, row in df.loc[(df[NEW_STEPS] != df[Names.STEPS]) & ~df[NEW_STEPS].isna()].iterrows():
            loader.add(Titles.STEPS, Units.STEPS_UNITS, None, row[Names.SOURCE], int(row[NEW_STEPS]),
                       time, StatisticJournalInteger, description=STEPS_DESCRIPTION)
        loader.load()
