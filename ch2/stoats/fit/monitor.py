from collections import defaultdict

from ..fit import Importer
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees, unpack_single_bytes
from ...lib.date import to_time
from ...lib.schedule import ZERO
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

    def _import(self, s, path):
        self._log.info('Importing monitor data from %s' % path)

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees, unpack_single_bytes)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else to_time(ZERO))]

        first_timestamp = self._first(path, records, MONITORING_INFO).timestamp
        last_timestamp = self._last(path, records, MONITORING).timestamp
        self._delete_journals(s, first_timestamp, path)
        mjournal = add(s, MonitorJournal(time=first_timestamp, fit_file=path, finish=last_timestamp))

        steps_to_date = defaultdict(lambda: 0)
        for record in records:
            if HEART_RATE in record.data:
                self._add_heart_rate(s, record, mjournal)
            if STEPS in record.data:
                for (activity, steps) in zip(record.data[ACTIVITY_TYPE][0], record.data[STEPS][0]):
                    steps_to_date[activity] = self._add_steps(s, record.timestamp, steps, steps_to_date[activity],
                                                              mjournal, path)

        s.flush()
        self._log.debug('Imported %d steps and %d heart rate values' %
                        (len(mjournal.steps), len(mjournal.heart_rate)))

    def _add_heart_rate(self, s, record, mjournal):
        add(s, MonitorHeartRate(time=record.timestamp, value=record.data[HEART_RATE][0],
                                monitor_journal=mjournal))

    def _add_steps(self, s, timestamp, steps, steps_to_date, mjournal, path):
        if steps is not None:
            if steps < steps_to_date:
                raise Exception('Decreasing steps in %s' % path)
            add(s, MonitorSteps(time=timestamp, value=steps-steps_to_date, monitor_journal=mjournal))
            steps_to_date = steps
        return steps_to_date
