
from ..fit import Importer
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees, unpack_single_bytes
from ...fit.profile.types import Date
from ...squeal.database import add
from ...squeal.tables.monitor import MonitorJournal, MonitorSteps, MonitorHeartRate


HEART_RATE = 'heart_rate'
STEPS = 'steps'


class MonitorImporter(Importer):

    def run(self, paths, force=False):
        self._run(paths, force=force)

    def _delete_journals(self, s, first_timestamp, path):
        if not first_timestamp:
            raise Exception('Missing timestamp in %s' % path)
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for mjournal in s.query(MonitorJournal). \
                filter(MonitorJournal.time == first_timestamp).all():
            s.delete(mjournal)
        s.flush()

    def _import(self, s, path):

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees, unpack_single_bytes)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else 0)]

        first_timestamp = self._first(path, records, 'monitoring_info').value.timestamp
        last_timestamp = self._last(path, records, 'monitoring_info').value.timestamp
        self._delete_journals(s, first_timestamp, path)
        mjournal = add(s, MonitorJournal(time=first_timestamp, fit_file=path, finish=last_timestamp))

        steps_to_date = 0
        for record in records:
            if HEART_RATE in record.data:
                self._add_heart_rate(s, record, mjournal)
            if STEPS in record.data:
                steps_to_date = self._add_steps(s, steps_to_date, record, mjournal, path)

    def _add_heart_rate(self, s, record, mjournal):
        add(s, MonitorHeartRate(time=Date.convert(record.timestamp), value=record.data[HEART_RATE][0],
                                monitor_journal=mjournal))

    def _add_steps(self, s, steps_to_date, record, mjournal, path):
        raw_value, steps = record.data[STEPS][0], None
        if isinstance(raw_value, tuple):
            data = dict(zip(record.data['activity_type'][0], raw_value))
            if 'walking' in data:
                steps = data['walking']
        else:
            steps = raw_value
        if steps is not None:
            if steps < steps_to_date:
                raise Exception('Decreasing steps in %s' % path)
            add(s, MonitorSteps(time=Date.convert(record.timestamp), value=steps-steps_to_date,
                                monitor_journal=mjournal))
            steps_to_date = steps
        return steps_to_date
