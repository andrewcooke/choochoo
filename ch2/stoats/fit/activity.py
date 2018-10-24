
from os.path import splitext, basename

from ..fit import AbortImport
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees
from ...lib.date import to_time
from ...lib.schedule import ZERO
from ...lib.utils import datetime_to_epoch
from ...squeal.database import add
from ...squeal.tables.activity import Activity, ActivityJournal, ActivityTimespan, ActivityWaypoint
from ...stoats.fit import Importer


class ActivityImporter(Importer):

    def run(self, paths, force=False, sport_to_activity=None):
        if sport_to_activity is None:
            raise Exception('No map from sport to activity')
        self._run(paths, force=force, sport_to_activity=sport_to_activity)

    def _activity(self, s, path, sport, sport_to_activity):
        if sport in sport_to_activity:
            return self._lookup_activity(s, sport_to_activity[sport])
        else:
            self._log.warn('Unrecognised sport: "%s" in %s' % (sport, path))
            raise AbortImport()

    def _lookup_activity(self, s, name):
        activity = s.query(Activity).filter(Activity.name == name).one_or_none()
        if not activity:
            activities = s.query(Activity).all()
            if activities:
                self._log.info('Available activities:')
                for activity in activities:
                    self._log.info('%s - %s' % (activity.name, activity.description))
            else:
                self._log.error('No activities defined - configure system correctly')
            raise Exception('Activity "%s" is not defined' % name)
        return activity

    def _delete_journals(self, s, activity, first_timestamp):
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for journal in s.query(ActivityJournal). \
                filter(ActivityJournal.activity == activity,
                       ActivityJournal.time == first_timestamp).all():
            s.delete(journal)
        s.flush()

    def _import(self, s, path, sport_to_activity):

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else to_time(0.0))]

        first_timestamp = self._first(path, records, 'event', 'record').value.timestamp
        sport = self._first(path, records, 'sport').value.sport.lower()
        activity = self._activity(s, path, sport, sport_to_activity)
        self._delete_journals(s, activity, first_timestamp)
        journal = add(s, ActivityJournal(activity=activity, time=first_timestamp,
                                         fit_file=path, name=splitext(basename(path))[0]))

        timespan, warned, latest = None, 0, to_time(0.0)
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
                                       (path, record.timestamp))
            except (AttributeError, TypeError) as e:
                if warned < 10:
                    self._log.warn('Error while reading %s - some data may be missing (%s)' % (path, e))
                elif warned == 10:
                    self._log.warn('No more warnings will be given for %s' % path)
                warned += 1