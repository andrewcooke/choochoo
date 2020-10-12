from logging import getLogger
from os.path import splitext, basename

from pygeotile.point import Point

from .utils import AbortImportButMarkScanned, ProcessFitReader
from ...commands.args import DEFAULT
from ...commands.upload import ACTIVITY
from ...common.date import to_time
from ...diary.model import TYPE, EDIT
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...fit.profile.profile import read_fit
from ...lib.io import split_fit_path
from ...names import N, T, U, Sports, S
from ...sql.database import StatisticJournalText
from ...sql.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...sql.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES, StatisticName, \
    StatisticJournalType, StatisticJournal, STATISTIC_JOURNAL_TYPES
from ...sql.tables.topic import ActivityTopicField, ActivityTopic, ActivityTopicJournal
from ...sql.utils import add
from ...srtm.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


# duplicate data in
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24715592701_tap-sync-18690-cc1dd93225119215a1ea87c584a974ce.fit
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24718989709_tap-sync-18690-effaaaffdd06b9419991471bd92d53d5.fit

class ActivityReader(ProcessFitReader):

    KIT = 'kit'

    def __init__(self, *args, sport_to_activity=None, record_to_db=None, **kargs):
        self.sport_to_activity = self._assert('sport_to_activity', sport_to_activity)
        self.record_to_db = [(field, title, units, STATISTIC_JOURNAL_CLASSES[type])
                             for field, (title, units, type)
                             in self._assert('record_to_db', record_to_db).items()]
        self.add_elevation = not any(title == T.ELEVATION for (field, title, units, type) in self.record_to_db)
        self.__ajournal = None  # save for coverage
        super().__init__(*args, sub_dir=ACTIVITY, **kargs)

    def _startup(self, s):
        self.__oracle = bilinear_elevation_from_constant(s)
        super()._startup(s)
        for field, title, units, cls in self.record_to_db:
            self._provides(s, title, STATISTIC_JOURNAL_TYPES[cls], units, None,
                           f'The value of field {field} in the FIT record.')
        self._provides(s, T.ELAPSED_TIME, StatisticJournalType.FLOAT, U.S, None,
                       'The time since the start of teh activity')
        self._provides(s, T.SPHERICAL_MERCATOR_X, StatisticJournalType.FLOAT, U.M, None,
                       'The Web Mercator EPSG:3857 X coordinate')
        self._provides(s, T.SPHERICAL_MERCATOR_Y, StatisticJournalType.FLOAT, U.M, None,
                       'The Web Mercator EPSG:3857 Y coordinate')
        self._provides(s, T.RAW_ELEVATION, StatisticJournalType.FLOAT, U.M, None,
                       'The elevation from SRTM1 at this location')
        self._provides(s, T.LON_LAT, StatisticJournalType.POINT, U.DEG, None,
                       'The WGS84 longitude and latitude')
        self._provides(s, T.KIT, StatisticJournalType.TEXT, None, None,
                       'The kit used in the activity')
        # also coverages - see _read

    def _read_kit(self, path):
        _, kit = split_fit_path(path)
        if kit:
            return kit
        else:
            log.debug(f'No {N.KIT} in {path}')
            return None

    def _read_data(self, s, file_scan):
        log.info('Reading activity data from %s' % file_scan)
        records = self.parse_records(read_fit(file_scan.path))
        kit = self._read_kit(file_scan.path)
        ajournal, activity_group, first_timestamp = self._create_activity(s, file_scan, kit, records)
        return ajournal, (ajournal, activity_group, first_timestamp, file_scan, kit, records)

    @staticmethod
    def parse_records(data):
        log.debug('Parsing records')
        records = ActivityReader.read_fit_file(data, merge_duplicates, fix_degrees, no_bad_values)
        log.debug('Parsed')
        return records

    @staticmethod
    def read_sport(path, records):
        try:
            return ActivityReader._first(path, records, 'sport').value.sport.lower()
        except AbortImportButMarkScanned:
            # alternative for some garmin devices (florian)
            return ActivityReader._first(path, records, 'session').value.sport.lower()

    @staticmethod
    def read_first_timestamp(path, records):
        return ActivityReader._first(path, records, 'event', 'record').value.timestamp

    @staticmethod
    def read_last_timestamp(path, records):
        return ActivityReader._last(path, records, 'event', 'record').value.timestamp

    def _create_activity(self, s, file_scan, kit, records):
        first_timestamp = self.read_first_timestamp(file_scan.path, records)
        last_timestamp = self.read_last_timestamp(file_scan.path, records)
        log.debug(f'Time range: {first_timestamp.timestamp()} - {last_timestamp.timestamp()}')
        sport = self.read_sport(file_scan.path, records)
        activity_group = self._activity_group(s, file_scan.path, sport, self.sport_to_activity, kit)
        log.info(f'{activity_group} from {sport} / {kit}')
        ajournal = add(s, ActivityJournal(activity_group=activity_group,
                                          start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                          file_hash_id=file_scan.file_hash_id))
        return ajournal, activity_group, first_timestamp

    def _activity_group(self, s, path, sport, lookup, kit):
        log.debug(f'Current lookup: {lookup}; sport: {sport}; kit: {kit}')
        if isinstance(lookup, str):
            return self._lookup_activity_group(s, lookup)
        if sport in lookup:
            return self._activity_group(s, path, sport, lookup[sport], kit)
        if N.KIT in lookup and kit in lookup[N.KIT]:
            return self._activity_group(s, path, sport, lookup[N.KIT][kit], kit)
        if DEFAULT in lookup:
            return self._activity_group(s, path, sport, lookup[DEFAULT], kit)
        log.warning('Unrecognised sport: "%s" in %s' % (sport, path))
        if sport in (Sports.SPORT_GENERIC,):
            raise AbortImportButMarkScanned(f'Ignoring {sport} entry')
        else:
            raise Exception(f'There is no group configured for {sport} entries in the FIT file.')

    def _lookup_activity_group(self, s, name):
        activity_group = ActivityGroup.from_name(s, name)
        if not activity_group:
            activities = s.query(ActivityGroup).all()
            if activities:
                log.info('Available activity group:')
                for activity_group in activities:
                    log.info('%s - %s' % (activity_group.name, activity_group.description))
            else:
                log.error('No activity groups defined - configure system correctly')
            raise Exception('ActivityGroup "%s" is not defined' % name)
        return activity_group

    @staticmethod
    def _save_name(s, ajournal, file_scan):
        from ...config.database import add_activity_topic_field
        log.debug('Saving name')
        # first, do we have the 'Name' field defined?
        # this should be triggered at most once per group if it was not already defined
        root = s.query(ActivityTopic). \
            filter(ActivityTopic.title == ActivityTopic.ROOT,
                   ActivityTopic.activity_group == ajournal.activity_group).one_or_none()
        if not root:
            root = add(s, ActivityTopic(title=ActivityTopic.ROOT, description=ActivityTopic.ROOT_DESCRIPTION,
                                        activity_group=ajournal.activity_group))
        if not s.query(ActivityTopicField). \
                join(StatisticName). \
                filter(StatisticName.name == N.NAME,
                       StatisticName.owner == ActivityTopic,
                       ActivityTopicField.activity_topic == root).one_or_none():
           add_activity_topic_field(s, root, T.NAME, -10, StatisticJournalType.TEXT,
                                     ajournal.activity_group, model={TYPE: EDIT},
                                     description=ActivityTopicField.NAME_DESCRIPTION)
        # second, do we already have a journal for this file, or do we need to add one?
        source = s.query(ActivityTopicJournal). \
            filter(ActivityTopicJournal.file_hash_id == file_scan.file_hash_id). \
            one_or_none()
        if not source:
            source = add(s, ActivityTopicJournal(file_hash_id=file_scan.file_hash_id,
                                                 activity_group=ajournal.activity_group))
        # and third, does that journal contain a name?
        if not s.query(StatisticJournal). \
                join(StatisticName). \
                filter(StatisticJournal.source == source,
                       StatisticName.owner == ActivityTopic,
                       StatisticName.name == N.NAME).one_or_none():
            value = splitext(basename(file_scan.path))[0]
            StatisticJournalText.add(s, N.NAME, None, None, ActivityTopic,
                                     source, value, ajournal.start)

    def _load_data(self, s, loader, data):

        ajournal, activity_group, first_timestamp, file_scan, kit, records = data
        timespan, warned, logged, last_timestamp = None, 0, 0, to_time(0.0)

        log.debug(f'Loading {self.record_to_db}')

        def is_event(record, *types):
            event = False
            if record.name == 'event':
                event = record.value.event == 'timer' and record.value.event_type in types
                if event: log.debug(f'{types} at {record.timestamp}')
            return event

        have_timespan = any(is_event(record, 'start') for record in records)
        only_records = list(filter(lambda x: x.name == 'record', records))
        final_timestamp = only_records[-1].timestamp

        if kit: loader.add_data(N.KIT, ajournal, kit, ajournal.start)

        self._save_name(s, ajournal, file_scan)
        self.__ajournal = ajournal

        if not have_timespan:
            first_timestamp = only_records[0].timestamp
            log.warning('Experimental handling of data without timespans')
            timespan = add(s, ActivityTimespan(activity_journal=ajournal, start=first_timestamp, finish=final_timestamp))

        for record in records:

            if have_timespan and is_event(record, 'start'):
                if timespan:
                    log.warning('Ignoring start with no corresponding stop (possible lost data?)')
                else:
                    timespan = add(s, ActivityTimespan(activity_journal=ajournal,
                                                       start=record.value.timestamp,
                                                       finish=record.value.timestamp))

            elif record.name == 'record':
                if record.value.timestamp > last_timestamp:
                    lat, lon, timestamp = None, None, record.value.timestamp
                    # elapsed time is not customizable because it needs extra processing
                    loader.add_data(T.ELAPSED_TIME, ajournal,
                                    (record.value.timestamp - first_timestamp).total_seconds(), timestamp)
                    # customizable loader
                    for field, title, units, type in self.record_to_db:
                        value = record.data.get(field, None)
                        if logged < 3:
                            log.debug(f'{title} = {value}')
                        if value is not None:
                            value = value[0][0]
                            if units == U.KM:  # internally everything uses M
                                value /= 1000
                            loader.add_data(title, ajournal, value, timestamp)
                            if title == T.LATITUDE:
                                lat = value
                            elif title == T.LONGITUDE:
                                lon = value
                    logged += 1
                    # values derived from lat/lon
                    if lat is not None and lon is not None:
                        loader.add_data(N.LON_LAT, ajournal, (lon, lat), timestamp)
                        x, y = Point.from_latitude_longitude(lat, lon).meters
                        loader.add_data(N.SPHERICAL_MERCATOR_X, ajournal, x, timestamp)
                        loader.add_data(N.SPHERICAL_MERCATOR_Y, ajournal, y, timestamp)
                        if self.add_elevation:
                            elevation = self.__oracle.elevation(lat, lon)
                            if elevation:
                                loader.add_data(N.RAW_ELEVATION, ajournal, elevation, timestamp)
                else:
                    log.warning('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                (file_scan.path, record.value.timestamp))
                last_timestamp = record.value.timestamp
                if not have_timespan:
                    ajournal.finish = record.value.timestamp

            elif have_timespan and is_event(record, 'stop_all', 'stop'):
                if timespan:
                    timespan.finish = record.value.timestamp
                    ajournal.finish = record.value.timestamp
                    timespan = None
                else:
                    log.debug('Ignoring stop with no corresponding start (possible lost data?)')

        if timespan:
            log.warning('Cleaning up dangling timespan')
            timespan.finish = final_timestamp

    def _read(self, s, path):
        loader = super()._read(s, path)
        for title, percent in loader.coverage_percentages():
            StatisticJournalFloat.add(s, T._cov(title), U.PC, S.join(S.MIN, S.AVG), self.owner_out,
                                      self.__ajournal, percent, self.__ajournal.start,
                                      description=f'Coverage (% of FIT records with data) for {title}.')
