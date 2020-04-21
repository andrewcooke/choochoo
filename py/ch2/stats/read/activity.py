import re
from logging import getLogger
from os.path import splitext, basename

from pygeotile.point import Point
from sqlalchemy.sql.functions import count

from ..names import LATITUDE, LONGITUDE, M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, ELEVATION, RAW_ELEVATION, \
    SPORT_GENERIC, COVERAGE, PC, MIN, summaries, AVG, KM
from ..read import MultiProcFitReader, AbortImportButMarkScanned
from ... import FatalException
from ...commands.args import ACTIVITIES, mm, FORCE, DEFAULT, KIT, DEFINE, no
from ...diary.model import TYPE, EDIT
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...lib.io import split_fit_path
from ...sql.database import Timestamp, StatisticJournalText
from ...sql.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...sql.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES, StatisticName, \
    StatisticJournalType, StatisticJournal
from ...sql.tables.topic import ActivityTopicField, ActivityTopic, ActivityTopicJournal
from ...sql.utils import add
from ...srtm.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


# duplicate data in
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24715592701_tap-sync-18690-cc1dd93225119215a1ea87c584a974ce.fit
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24718989709_tap-sync-18690-effaaaffdd06b9419991471bd92d53d5.fit

class ActivityReader(MultiProcFitReader):

    def __init__(self, *args, define=None, sport_to_activity=None, record_to_db=None, kit=True, **kargs):
        from ...commands.upload import ACTIVITY
        self.define = define if define else {}
        self.kit = kit
        self.sport_to_activity = self._assert('sport_to_activity', sport_to_activity)
        self.record_to_db = [(field, name, units, STATISTIC_JOURNAL_CLASSES[type])
                             for field, (name, units, type)
                             in self._assert('record_to_db', record_to_db).items()]
        self.add_elevation = not any(name == ELEVATION for (field, name, units, type) in self.record_to_db)
        self.__ajournal = None  # save for coverage
        super().__init__(*args, sub_dir=ACTIVITY, **kargs)

    def _base_command(self):
        if self.define:
            define = ' '.join(f'{mm(DEFINE)} "{name}={value}"' for name, value in self.define.items()) + ' -- '
        else:
            define = ''
        force = ' ' + mm(FORCE) if self.force else ''
        nokit = ' ' + mm(no(KIT)) if not self.kit else ''
        return f'{ACTIVITIES}{force}{define}{nokit}'

    def _startup(self, s):
        super()._startup(s)
        self.__oracle = bilinear_elevation_from_constant(s)

    def _build_define(self, path):
        define = dict(self.define)
        if self.kit:
            _, kit = split_fit_path(path)
            if kit:
                log.debug(f'Adding {KIT}={kit} to definitions')
                define[KIT] = kit
            else:
                log.debug(f'No kit in {path}')
        return define

    def _read_data(self, s, file_scan):
        log.info('Reading activity data from %s' % file_scan)
        records = self.parse_records(read_fit(file_scan.path))
        define = self._build_define(file_scan.path)
        ajournal, activity_group, first_timestamp = self._create_activity(s, file_scan, define, records)
        return ajournal, (ajournal, activity_group, first_timestamp, file_scan, define, records)

    @staticmethod
    def parse_records(data):
        return ActivityReader.read_fit_file(data, merge_duplicates, fix_degrees, no_bad_values)

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

    def _create_activity(self, s, file_scan, define, records):
        first_timestamp = self.read_first_timestamp(file_scan.path, records)
        last_timestamp = self.read_last_timestamp(file_scan.path, records)
        log.debug(f'Time range: {first_timestamp.timestamp()} - {last_timestamp.timestamp()}')
        sport = self.read_sport(file_scan.path, records)
        activity_group = self._activity_group(s, file_scan.path, sport, self.sport_to_activity, define)
        log.info(f'{activity_group} from {sport} / {define}')
        if self.force:
            self._delete_journals(s, activity_group, first_timestamp, last_timestamp, file_scan)
        else:
            self._check_journals(s, activity_group, first_timestamp, last_timestamp, file_scan)
        ajournal = add(s, ActivityJournal(activity_group=activity_group,
                                          start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                          file_hash_id=file_scan.file_hash_id))
        return ajournal, activity_group, first_timestamp

    def _activity_group(self, s, path, sport, lookup, define):
        log.debug(f'Current lookup: {lookup}; sport: {sport}; define: {define}')
        if isinstance(lookup, str):
            return self._lookup_activity_group(s, lookup)
        if sport in lookup:
            return self._activity_group(s, path, sport, lookup[sport], define)
        for key, values in define.items():
            for value in values.split(','):
                if key in lookup and value in lookup[key]:
                    return self._activity_group(s, path, sport, lookup[key][value], define)
        if DEFAULT in lookup:
            return self._activity_group(s, path, sport, lookup[DEFAULT], define)
        log.warning('Unrecognised sport: "%s" in %s' % (sport, path))
        if sport in (SPORT_GENERIC,):
            raise Exception(f'Ignoring {sport} entry')
        else:
            raise FatalException(f'There is no group configured for {sport} entries in the FIT file.')

    def _lookup_activity_group(self, s, name):
        activity_group = ActivityGroup.from_name(s, name, optional=True)
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

    def _overlapping_journals(self, s, what, activity_group, first_timestamp, last_timestamp):
        return s.query(what). \
                filter(ActivityJournal.activity_group == activity_group,
                       ActivityJournal.start < last_timestamp,
                       ActivityJournal.finish >= first_timestamp)

    def _file_hash_journals(self, s, what, file_scan):
        return s.query(what). \
                filter(ActivityJournal.file_hash == file_scan.file_hash)

    def _delete_query(self, s, query):
        for journal in query.all():
            Timestamp.clear(s, owner=self.owner_out, source=journal)
            log.debug(f'Deleting {journal}')
            s.delete(journal)

    def _delete_journals(self, s, activity_group, first_timestamp, last_timestamp, file_scan):
        log.debug('Deleting overlapping journals')
        self._delete_query(s, self._overlapping_journals(s, ActivityJournal, activity_group,
                                                         first_timestamp, last_timestamp))
        log.debug('Deleting journals from same file')
        self._delete_query(s, self._file_hash_journals(s, ActivityJournal, file_scan))
        s.commit()

    def _check_journals(self, s, activity_group, first_timestamp, last_timestamp, file_scan):
        log.debug('Checking for overlapping journals')
        if self._overlapping_journals(s, count(ActivityJournal.id), activity_group,
                                      first_timestamp, last_timestamp).scalar():
            log.warning(f'Overlapping activities for {first_timestamp} - {last_timestamp}')
            raise AbortImportButMarkScanned()
        log.debug('Checking for previous file')
        if self._file_hash_journals(s, count(ActivityJournal.id), file_scan).scalar():
            log.warning(f'Repeated scan of file {file_scan.path}')
            raise Exception(file_scan.path)  # this should not happen since hash is checked before import

    def _load_define(self, s, define, ajournal):
        for name, value in define.items():
            log.debug(f'Setting {name} = {value}')
            StatisticJournalText.add(s, name, None, None, self.owner_out, ajournal.activity_group,
                                     ajournal, value, ajournal.start)

    @staticmethod
    def _save_name(s, ajournal, file_scan):
        from ...config import add_activity_topic_field
        log.debug('Saving name')
        # first, do we have the 'Name' field defined for all activities?
        # this should be triggered at most once if it was not already defined
        if not s.query(ActivityTopicField). \
                join(StatisticName). \
                filter(StatisticName.name == ActivityTopicField.NAME,
                       StatisticName.constraint == ajournal.activity_group,
                       StatisticName.owner == ActivityTopic,
                       ActivityTopicField.activity_topic_id == None).one_or_none():
            add_activity_topic_field(s, None, ActivityTopicField.NAME, -10, StatisticJournalType.TEXT,
                                     ajournal.activity_group, model={TYPE: EDIT})
        # second, do we already have a journal for this file, or do we need to add one?
        source = s.query(ActivityTopicJournal). \
            filter(ActivityTopicJournal.file_hash_id == file_scan.file_hash_id). \
            one_or_none()
        if not source:
            source = add(s, ActivityTopicJournal(file_hash_id=file_scan.file_hash_id))
        # and third, does that journal contain a name?
        if not s.query(StatisticJournal). \
                join(StatisticName). \
                filter(StatisticJournal.source == source,
                       StatisticName.owner == ActivityTopic,
                       StatisticName.constraint == ajournal.activity_group,
                       StatisticName.name == ActivityTopicField.NAME). \
                one_or_none():
            value = splitext(basename(file_scan.path))[0]
            StatisticJournalText.add(s, ActivityTopicField.NAME, None, None, ActivityTopic, ajournal.activity_group,
                                     source, value, ajournal.start)

    def _load_data(self, s, loader, data):

        ajournal, activity_group, first_timestamp, file_scan, define, records = data
        timespan, warned, logged, last_timestamp = None, 0, 0, to_time(0.0)
        self._load_define(s, define, ajournal)
        self._save_name(s, ajournal, file_scan)
        self.__ajournal = ajournal

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
        if not have_timespan:
            first_timestamp = only_records[0].timestamp
            log.warning('Experimental handling of data without timespans')
            timespan = add(s, ActivityTimespan(activity_journal=ajournal, start=first_timestamp))

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
                    # customizable loader
                    for field, name, units, type in self.record_to_db:
                        value = record.data.get(field, None)
                        if logged < 3:
                            log.debug(f'{name} = {value}')
                        if value is not None:
                            value = value[0][0]
                            if units == KM:  # internally everything uses M
                                value /= 1000
                            loader.add(name, units, None, activity_group, ajournal, value, timestamp, type,
                                       description=f'The value of field {field} in the FIT record.')
                            if name == LATITUDE:
                                lat = value
                            elif name == LONGITUDE:
                                lon = value
                    logged += 1
                    # values derived from lat/lon
                    if lat is not None and lon is not None:
                        x, y = Point.from_latitude_longitude(lat, lon).meters
                        loader.add(SPHERICAL_MERCATOR_X, M, None, activity_group, ajournal, x, timestamp,
                                   StatisticJournalFloat, description='The WGS84 X coordinate')
                        loader.add(SPHERICAL_MERCATOR_Y, M, None, activity_group, ajournal, y, timestamp,
                                   StatisticJournalFloat, description='The WGS84 Y coordinate')
                        if self.add_elevation:
                            elevation = self.__oracle.elevation(lat, lon)
                            if elevation:
                                loader.add(RAW_ELEVATION, M, None, activity_group, ajournal, elevation, timestamp,
                                           StatisticJournalFloat,
                                           description='The elevation from SRTM1 at this location')
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
        for (name, constraint), percent in loader.coverage_percentages():
            StatisticJournalFloat.add(s, COVERAGE, PC, summaries(MIN, AVG), self.owner_out,
                                      f'{name} / {constraint.name}', self.__ajournal, percent,
                                      self.__ajournal.start)
        s.commit()
