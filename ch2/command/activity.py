
from glob import glob
from os import stat
from os.path import isdir, join, basename, splitext

from ..command.args import PATH, ACTIVITY, FORCE
from ..fit.format.read import filtered_records
from ..fit.format.records import fix_degrees
from ..fit.profile.types import timestamp_to_datetime
from ..lib.utils import datetime_to_epoch
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, FileScan, ActivityJournal, ActivityTimespan, ActivityWaypoint
from ..stoats import run_statistics


def activity(args, log):
    '''
# activity

    ch2 activity ACTIVITY PATH

Read one or more (if PATH is a directory) FIT files and associated them with the given activity type.
    '''
    db = Database(args, log)
    force = args[FORCE]
    activity = args[ACTIVITY][0]
    path = args.path(PATH, index=0, rooted=False)
    FITImporter(log, db, activity, path).run(force=force)
    run_statistics(log, db, force=force)


class FITImporter:

    def __init__(self, log, db, activity, path):
        self._log = log
        self._db = db
        self._activity_name = activity
        self._path = path

    def run(self, force=False):
        with self._db.session_context() as s:
            activity = Activity.lookup(self._log, s, self._activity_name)
            for file in self._modified_files(s, force):
                self._log.info('Scanning %s' % file)
                self._import(s, file, activity, force)

    def _modified_files(self, s, force):
        path = self._path
        if isdir(path):
            path = join(path, '*.fit')
        files = list(sorted(glob(path)))
        if not files:
            raise Exception('No match for "%s"' % self._path)
        for file in files:
            scan = s.query(FileScan).filter(FileScan.path == file).one_or_none()
            if not scan:
                scan = FileScan(path=file, last_scan=0)
                s.add(scan)
            last_modified = stat(file).st_mtime
            if force or last_modified > scan.last_scan:
                yield file
                scan.last_scan = last_modified
            else:
                self._log.debug('Skipping %s (already scanned)' % file)

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
