
from os.path import splitext, basename

from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees
from ...fit.profile.types import timestamp_to_datetime
from ...lib.io import modified_files
from ...lib.utils import datetime_to_epoch
from ...squeal.database import add
from ...squeal.tables.activity import Activity, ActivityJournal, ActivityTimespan, ActivityWaypoint


class AbortImport(Exception):
    pass


class ActivityImporter:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, paths, force=False, sport_to_activity=None):
        if sport_to_activity is None:
            raise Exception('No map from sport to activity')
        with self._db.session_context() as s:
            files = list(modified_files(self._log, s, paths, force=force))
        for file in files:
            self._log.info('Scanning %s' % file)
            with self._db.session_context() as s:
                try:
                    self._import(s, file, sport_to_activity)
                except AbortImport:
                    self._log.debug('Aborted %s' % file)

    def _first(self, path, records, *names):
        try:
            return next(iter(record for record in records if record.name in names))
        except:
            self._log.warn('No %s entry(s) in %s' % (str(names), path))
            raise AbortImport()

    def _activity(self, s, path, sport, sport_to_activity):
        if sport in sport_to_activity:
            return Activity.lookup(self._log, s, sport_to_activity[sport])
        else:
            self._log.warn('Unrecognised sport: "%s" in %s' % (sport, path))
            self._log.warn('Unrecognised sport: "%s" in %s' % (sport, path))
            raise AbortImport()

    def _delete_journals(self, s, activity, first_timestamp):
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for journal in s.query(ActivityJournal). \
                filter(ActivityJournal.activity == activity,
                       ActivityJournal.time == first_timestamp).all():
            s.delete(journal)

    def _import(self, s, path, sport_to_activity):

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else 0)]

        first_timestamp = self._first(path, records, 'event', 'record').value.timestamp
        sport = self._first(path, records, 'sport').value.sport.lower()
        activity = self._activity(s, path, sport, sport_to_activity)
        self._delete_journals(s, activity, first_timestamp)
        journal = add(s, ActivityJournal(activity=activity, time=first_timestamp,
                                         fit_file=path, name=splitext(basename(path))[0]))

        timespan, warned, latest = None, 0, 0
        for record in records:
            try:
                if record.name == 'event' or (record.name == 'record' and record.timestamp > latest):
                    if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                        timespan = add(s, ActivityTimespan(activity_journal=journal,
                                                           start=datetime_to_epoch(record.value.timestamp)))
                    if record.name == 'record':
                        waypoint = add(s, ActivityWaypoint(activity_journal=journal,
                                                           activity_timespan=timespan,
                                                           time=datetime_to_epoch(record.value.timestamp),
                                                           latitude=record.none.position_lat,
                                                           longitude=record.none.position_long,
                                                           heart_rate=record.none.heart_rate,
                                                           # if distance is not set in some future file, calculate from
                                                           # lat/long?
                                                           distance=record.value.distance,
                                                           speed=record.none.enhanced_speed))
                    if record.name == 'event' and record.value.event == 'timer' \
                            and record.value.event_type == 'stop_all':
                        if timespan:
                            timespan.finish = datetime_to_epoch(record.value.timestamp)
                            journal.finish = record.value.timestamp
                            timespan = None
                        else:
                            self._log.warn('Ignoring stop with no corresponding start (possible lost data?)')
                    if record.name == 'record':
                        latest = record.timestamp
                else:
                    if record.name == 'record':
                        self._log.warn('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                       (path, timestamp_to_datetime(record.timestamp)))
            except (AttributeError, TypeError) as e:
                if warned < 10:
                    self._log.warn('Error while reading %s - some data may be missing (%s)' % (path, e))
                elif warned == 10:
                    self._log.warn('No more warnings will be given for %s' % path)
                warned += 1