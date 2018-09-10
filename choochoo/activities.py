
from collections.__init__ import deque, Counter
from glob import glob
from itertools import chain
from os import stat
from os.path import isdir, join, basename, splitext

from sqlalchemy.orm.exc import NoResultFound
from urwid import Edit, Pile, Columns, connect_signal

from .args import PATH, ACTIVITY, EDIT_ACTIVITIES, FORCE, MONTH, YEAR
from .fit.format.read import filtered_records
from .fit.profile.types import timestamp_to_datetime
from .lib.io import tui
from .squeal.database import Database
from .squeal.tables.activity import Activity, FileScan, ActivityDiary, ActivityTimespan, ActivityWaypoint, \
    ActivityStatistic
from .squeal.tables.heartrate import HeartRateZones
from .squeal.tables.statistic import Statistic
from .statistics import round_km, ACTIVE_SPEED, ACTIVE_TIME, MEDIAN_KM_TIME, PERCENT_IN_Z, TIME_IN_Z, \
    MAX_MED_HR_OVER_M, MAX, BPM, PC, S, KMH, HR_MINUTES, M, ACTIVE_DISTANCE
from .summary import regular_summary
from .utils import datetime_to_epoch
from .uweird.editor import EditorApp
from .uweird.factory import Factory
from .uweird.focus import MessageBar, FocusWrap
from .uweird.widgets import SquareButton, ColSpace


class ActivityWidget(FocusWrap):

    def __init__(self, log, tabs, bar, outer):
        self.__outer = outer
        factory = Factory(tabs=tabs, bar=bar)
        self.title = factory(Edit(caption='Title: '))
        self.sort = factory(Edit(caption='Sort: '))
        self.delete = SquareButton('Delete')
        delete = factory(self.delete, message='delete from database')
        self.reset = SquareButton('Reset')
        reset = factory(self.reset, message='reset from database')
        self.description = factory(Edit(caption='Description: ', multiline=True))
        super().__init__(
            Pile([self.title,
                  Columns([(20, self.sort),
                           ColSpace(),
                           (10, delete),
                           (9, reset)
                           ]),
                  self.description,
                  ]))

    def connect(self, binder):
        connect_signal(self.reset, 'click', lambda widget: binder.reset())
        connect_signal(self.delete, 'click', lambda widget: self.__on_delete(widget, binder))

    def __on_delete(self, _unused_widget, binder):
        binder.delete()
        self.__outer.remove(self)


@tui
def edit_activities(args, log):
    '''
# edit-activities

    ch2 edit-activities

The interactive editor for activities.  Allows addition, deletion and modification of activities.

Once added, activities can be imported and will appear in the diary.

To exit, alt-q (or, without saving, Alt-x).
    '''
    session = Database(args, log).session()
    EditorApp(log, session, MessageBar(), "Activities", ActivityWidget, Activity).run()


def add_activity(args, log):
    '''
# add-activity

    ch2 add-activity ACTIVITY PATH

Read one or more (if PATH is a directory) FIT files and associated them with the given activity type.
    '''
    db = Database(args, log)
    force = args[FORCE]
    activity_title = args[ACTIVITY][0]
    with db.session_context() as session:
        try:
            activity = session.query(Activity).filter(Activity.title == activity_title).one()
        except NoResultFound:
            if force:
                activity = Activity(title=activity_title)
                session.add(activity)
            else:
                raise Exception('Activity "%s" is not defined - see ch2 %s' % (activity, EDIT_ACTIVITIES))

    path = args.path(PATH, index=0, rooted=False)
    if isdir(path):
        path = join(path, '*.fit')
    files = list(sorted(glob(path)))
    if not files:
        raise Exception('No match for "%s"' % path)
    for file in files:
        with db.session_context() as session:
            try:
                scan = session.query(FileScan).filter(FileScan.path == file).one()
            except NoResultFound:
                scan = FileScan(path=file, last_scan=0)
                session.add(scan)
            last_modified = stat(file).st_mtime
            if force or last_modified > scan.last_scan:
                log.info('Scanning %s' % file)
                diary = add_file(log, session, activity, file, force)
                add_stats(log, session, diary)
                scan.last_scan = last_modified
            else:
                log.debug('Skipping %s (already scanned)' % file)
                session.expunge(scan)
    if args[MONTH] or args[YEAR]:
        regular_summary(args[MONTH], activity_title, force, db, log)


def add_file(log, session, activity, path, force):
    if force:
        session.query(ActivityDiary).filter(ActivityDiary.fit_file == path).delete()
    data, types, messages, records = filtered_records(log, path)
    diary = ActivityDiary(activity=activity, fit_file=path, title=splitext(basename(path))[0])
    session.add(diary)
    timespan, warned, latest = None, 0, 0
    for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else 0):
        record = record.force()
        try:
            if record.name == 'event' or (record.name == 'record' and record.timestamp > latest):
                if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                    if not diary.start:
                        diary.date = record.value.timestamp
                        diary.start = record.value.timestamp
                    timespan = ActivityTimespan(activity_diary=diary,
                                                start=datetime_to_epoch(record.value.timestamp))
                    session.add(timespan)
                if record.name == 'record':
                    waypoint = ActivityWaypoint(activity_diary=diary,
                                                activity_timespan=timespan,
                                                epoch=datetime_to_epoch(record.value.timestamp),
                                                latitude=record.none.position_lat,
                                                longitude=record.none.position_long,
                                                hr=record.none.heart_rate,
                                                # if distance is not set in some future file, calculate from
                                                # lat/long?
                                                distance=record.value.distance,
                                                speed=record.none.enhanced_speed)
                    session.add(waypoint)
                if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'stop_all':
                    timespan.finish = datetime_to_epoch(record.value.timestamp)
                    diary.finish = record.value.timestamp
                    timespan = None
                if record.name == 'record':
                    latest = record.timestamp
            else:
                if record.name == 'record':
                    log.warn('Ignoring duplicate record data for %s at %s - some data may be missing' %
                             (path, timestamp_to_datetime(record.timestamp)))
        except (AttributeError, TypeError) as e:
            if warned < 10:
                log.warn('Error while reading %s - some data may be missing (%s)' % (path, e))
            elif warned == 10:
                log.warn('No more warnings will be given for %s' % path)
            warned += 1
    return diary


class Chunk:

    def __init__(self, waypoint):
        self.__timespan = waypoint.activity_timespan
        self.__waypoints = deque([waypoint])

    def append(self, waypoint):
        self.__waypoints.append(waypoint)

    def popleft(self):
        return self.__waypoints.popleft()

    def __diff(self, index, attr):
        if len(self.__waypoints) > 1:
            return attr(self.__waypoints[index]) - attr(self.__waypoints[0])
        else:
            return 0

    def distance(self):
        return self.__diff(-1, lambda w: w.distance)

    def distance_delta(self):
        return self.__diff(1, lambda w: w.distance)

    def time(self):
        return self.__diff(-1, lambda w: w.epoch)

    def time_delta(self):
        return self.__diff(1, lambda w: w.epoch)

    def hrs(self):
        return (waypoint.hr for waypoint in self.__waypoints if waypoint.hr is not None)

    def __len__(self):
        return len(self.__waypoints)

    def __getitem__(self, item):
        return self.__waypoints[item]

    def __bool__(self):
        return self.distance_delta() > 0


class Chunks:

    def __init__(self, log, diary):
        self._log = log
        self.__diary = diary

    def chunks(self):
        chunks, chunk_index = deque(), {}
        for waypoint in self.__diary.waypoints:
            timespan = waypoint.activity_timespan
            if timespan:
                if timespan in chunk_index:
                    chunk_index[timespan].append(waypoint)
                else:
                    chunk = Chunk(waypoint)
                    chunk_index[timespan] = chunk
                    chunks.append(chunk)
                yield chunks


class TimeForDistance(Chunks):

    def __init__(self, log, diary, distance):
        super().__init__(log, diary)
        self.__distance = distance

    def times(self):
        for chunks in self.chunks():
            distance = sum(chunk.distance() for chunk in chunks)
            if distance > self.__distance:
                while chunks and distance - chunks[0].distance_delta() > self.__distance:
                    distance -= chunks[0].distance_delta()
                    chunks[0].popleft()
                    if not chunks[0]:
                        chunks.popleft()
                time = sum(chunk.time() for chunk in chunks)
                yield time * self.__distance / distance


class MedianHRForTime(Chunks):

    def __init__(self, log, diary, time, max_gap=None):
        super().__init__(log, diary)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].activity_timespan.start - c2[0].activity_timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks))

    def hrs(self):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                self._log.debug('Rejecting chunk because of gap (%ds)' % int(self._max_gap(chunks)))
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    chunks[0].popleft()
                    while chunks and not chunks[0]:
                        chunks.popleft()
                hrs = list(sorted(chain(*(chunk.hrs() for chunk in chunks))))
                if hrs:
                    median = len(hrs) // 2
                    yield hrs[median]


class Totals(Chunks):

    def __init__(self, log, diary):
        super().__init__(log, diary)
        chunks = list(self.chunks())[-1]
        self.distance = sum(chunk.distance() for chunk in chunks)
        self.time = sum(chunk.time() for chunk in chunks)


class Zones(Chunks):

    def __init__(self, log, diary, zones):
        super().__init__(log, diary)
        # this assumes record data are evenly distributed
        self.zones = []
        chunks = list(self.chunks())[-1]
        counts = Counter()
        lower = 0
        for zone, upper in enumerate(zone.upper for zone in zones.zones):
            for chunk in chunks:
                for hr in chunk.hrs():
                    if hr is not None:
                        if lower <= hr < upper:
                            counts[zone] += 1
            lower = upper
        total = sum(counts.values())
        if total:
            for zone in range(len(zones.zones)):
                self.zones.append((zone + 1, counts[zone] / total))


def add_stat(log, session, diary, name, best, value, units):
    statistic = session.query(Statistic).filter(
        Statistic.name == name, Statistic.activity == diary.activity).one_or_none()
    if not statistic:
        statistic = Statistic(activity=diary.activity, name=name, units=units, best=best)
        session.add(statistic)
    statistic = ActivityStatistic(statistic=statistic, activity_diary=diary, value=value)
    session.add(statistic)
    log.info(statistic)


def add_stats(log, session, diary):
    totals = Totals(log, diary)
    add_stat(log, session, diary, ACTIVE_DISTANCE, MAX, totals.distance, M)
    add_stat(log, session, diary, ACTIVE_TIME, MAX, totals.time, S)
    add_stat(log, session, diary, ACTIVE_SPEED, MAX, totals.distance * 3.6 / totals.time, KMH)
    for target in round_km():
        times = list(sorted(TimeForDistance(log, diary, target * 1000).times()))
        if not times:
            break
        median = len(times) // 2
        add_stat(log, session, diary, MEDIAN_KM_TIME % target, 'min', times[median], S)
    zones = session.query(HeartRateZones).filter(HeartRateZones.date <= diary.date)\
        .order_by(HeartRateZones.date.desc()).limit(1).one_or_none()
    if zones:
        for (zone, frac) in Zones(log, diary, zones).zones:
            add_stat(log, session, diary, PERCENT_IN_Z % zone, None, 100 * frac, PC)
        for (zone, frac) in Zones(log, diary, zones).zones:
            add_stat(log, session, diary, TIME_IN_Z % zone,  None, frac * totals.time, S)
        for target in HR_MINUTES:
            hrs = sorted(MedianHRForTime(log, diary, target * 60).hrs(), reverse=True)
            if hrs:
                add_stat(log, session, diary, MAX_MED_HR_OVER_M % target, MAX, hrs[0], BPM)
    else:
        log.warn('No HR zones defined for %s or before' % diary.date)
