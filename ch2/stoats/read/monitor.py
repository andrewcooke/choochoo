
import datetime as dt
from collections import defaultdict

from sqlalchemy import desc

from ..read import Importer
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees, unpack_single_bytes
from ...lib.date import to_time, time_to_local_date
from ...squeal.database import add
from ...squeal.tables.monitor import MonitorJournal, MonitorSteps, MonitorHeartRate

ACTIVITY_TYPE = 'activity_type'
HEART_RATE = 'heart_rate'
MONITORING = 'monitoring'
MONITORING_INFO = 'monitoring_info'
STEPS = 'steps'


class MonitorImporter(Importer):

    def run(self, paths, force=False):
        self._run(paths, force=force)

    def _delete_journals(self, s, first_timestamp, path):
        # key only on time so that repeated files don't affect things
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % path)
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.time == first_timestamp).all():
            self._log.debug('Deleting %s' % mjournal)
            s.delete(mjournal)
        s.flush()

    def _delta(self, steps, activity, prev_steps):
        if steps >= prev_steps[activity]:
            delta = steps - prev_steps[activity]
        else:
            delta = steps
        prev_steps[activity] = steps
        return delta

    def _set_from_previous(self, s, first_timestamp, prev_steps):
        prev = s.query(MonitorJournal). \
            filter(MonitorJournal.finish <= first_timestamp). \
            order_by(desc(MonitorJournal.finish)).limit(1).one_or_none()
        if prev:
            for step in prev.steps:
                prev_steps[step.activity] = step.value

    def _update_next(self, s, last_timestamp, prev_steps):
        next = s.query(MonitorJournal). \
            filter(MonitorJournal.time >= last_timestamp). \
            order_by(MonitorJournal.time).limit(1).one_or_none()
        if next:
            for step in next.steps:
                step.delta = self._delta(step.value, step.activity, prev_steps)

    def _import(self, s, path):
        self._log.info('Importing monitor data from %s' % path)

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees, unpack_single_bytes)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else to_time(0.0))]

        first_timestamp = self._first(path, records, MONITORING_INFO).timestamp
        last_timestamp = self._last(path, records, MONITORING).timestamp
        self._delete_journals(s, first_timestamp, path)
        mjournal = add(s, MonitorJournal(time=first_timestamp, fit_file=path, finish=last_timestamp))

        prev_steps = defaultdict(lambda: 0)
        self._set_from_previous(s, first_timestamp, prev_steps)

        for record in records:
            if HEART_RATE in record.data:
                self._add_heart_rate(s, record, mjournal)
            if STEPS in record.data:
                for (activity, steps) in zip(record.data[ACTIVITY_TYPE][0], record.data[STEPS][0]):
                    self._add_steps(s, record.timestamp, steps, prev_steps, activity, mjournal)

        self._update_next(s, last_timestamp, prev_steps)

        self._log.debug('Imported %d steps and %d heart rate values' %
                        (len(mjournal.steps), len(mjournal.heart_rate)))

    def _add_heart_rate(self, s, record, mjournal):
        add(s, MonitorHeartRate(time=record.timestamp, value=record.data[HEART_RATE][0],
                                monitor_journal=mjournal))

    def _add_steps(self, s, timestamp, steps, prev_steps, activity, mjournal):
        add(s, MonitorSteps(time=timestamp, value=steps,
                            delta=self._delta(steps, activity, prev_steps),
                            activity=activity, monitor_journal=mjournal))


def missing_dates(log, s):
    # we don't try to be perfect here.  the idea is that it's called to get the latest
    # updates, rather than fill in all gaps (do the bulk download thing for that).
    # we also don't try to get fractional data.
    # and as for timezones... we just assume garmin uses the local timezone.
    latest = s.query(MonitorJournal).order_by(desc(MonitorJournal.time)).limit(1).one_or_none()
    if latest is None:
        log.warn('No exiting monitor data - ' +
                 'do a bulk download instead: https://www.garmin.com/en-US/account/datamanagement/')
        return
    # find the mid-point to avoid any problems with timezones and edge cases
    # (these files don't span more than a day)
    seconds = (latest.finish - latest.time).total_seconds() / 2
    start = time_to_local_date(latest.time + dt.timedelta(seconds=seconds) + dt.timedelta(days=1))
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
        log.warn('No dates to download')