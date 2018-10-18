
from glob import glob
from os import stat
from os.path import isdir, join, basename, splitext

from ch2.lib.io import glob_modified_files
from ..command.args import PATH, ACTIVITY, FORCE, FAST
from ..fit.format.read import filtered_records
from ..fit.format.records import fix_degrees
from ..fit.profile.types import timestamp_to_datetime
from ..lib.utils import datetime_to_epoch
from ..squeal.tables.activity import Activity, FileScan, ActivityJournal, ActivityTimespan, ActivityWaypoint
from ..stoats.calculate import run_statistics


def activity(args, log, db):
    '''
# activity

    ch2 activity ACTIVITY PATH

Read one or more (if PATH is a directory) FIT files and associated them with the given activity type.
    '''
    force, fast = args[FORCE], args[FAST]
    activity = args[ACTIVITY][0]
    path = args.path(PATH, index=0, rooted=False)
    ActivityImporter(log, db, activity, path).run(force=force)
    if not fast:
        run_statistics(log, db, force=force)


class ActivityImporter:

    def __init__(self, log, db, activity, path):
        self._log = log
        self._db = db
        self._activity_name = activity
        self._path = path

    def run(self, force=False):
        with self._db.session_context() as s:
            activity = Activity.lookup(self._log, s, self._activity_name)
            for file in glob_modified_files(self._log, s, self._path, force=force):
                self._log.info('Scanning %s' % file)
                self._import(s, file, activity, force)

    def _import(self, s, path, activity, force):

        if force:
            s.query(ActivityJournal).filter(ActivityJournal.fit_file == path).delete()
        data, types, messages, records = filtered_records(self._log, path)
        journal = ActivityJournal(activity=activity, fit_file=path, name=splitext(basename(path))[0])
        s.add(journal)

        timespan, warned, latest = None, 0, 0
        for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else 0):
            record = record.force(fix_degrees)
            try:
                if record.name == 'event' or (record.name == 'record' and record.timestamp > latest):
                    if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                        if not journal.time:
                            journal.time = record.value.timestamp
                        timespan = ActivityTimespan(activity_journal=journal,
                                                    start=datetime_to_epoch(record.value.timestamp))
                        s.add(timespan)
                    if record.name == 'record':
                        waypoint = ActivityWaypoint(activity_journal=journal,
                                                    activity_timespan=timespan,
                                                    time=datetime_to_epoch(record.value.timestamp),
                                                    latitude=record.none.position_lat,
                                                    longitude=record.none.position_long,
                                                    heart_rate=record.none.heart_rate,
                                                    # if distance is not set in some future file, calculate from
                                                    # lat/long?
                                                    distance=record.value.distance,
                                                    speed=record.none.enhanced_speed)
                        s.add(waypoint)
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
                raise e
                if warned < 10:
                    self._log.warn('Error while reading %s - some data may be missing (%s)' % (path, e))
                elif warned == 10:
                    self._log.warn('No more warnings will be given for %s' % path)
                warned += 1
