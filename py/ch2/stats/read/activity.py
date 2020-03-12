
from logging import getLogger
from os.path import splitext, basename

from pygeotile.point import Point
from sqlalchemy.sql.functions import count

from ..names import LATITUDE, LONGITUDE, M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, ELEVATION, RAW_ELEVATION, \
    SPORT_GENERIC, COVERAGE, PC, MIN, summaries, AVG, KM
from ..read import MultiProcFitReader, AbortImportButMarkScanned
from ... import FatalException
from ...commands.args import ACTIVITIES, WORKER, FAST, mm, FORCE, VERBOSITY, LOG
from ...diary.model import TYPE, EDIT
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...lib.date import to_time
from ...sql.database import Timestamp, StatisticJournalText
from ...sql.tables.topic import ActivityTopicField, ActivityTopic, ActivityTopicJournal
from ...sql.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...sql.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES, StatisticName, \
    StatisticJournalType, StatisticJournal
from ...sql.utils import add
from ...srtm.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


# duplicate data in
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24715592701_tap-sync-18690-cc1dd93225119215a1ea87c584a974ce.fit
# /home/andrew/archive/fit/batch/DI_CONNECT/DI-Connect-Fitness/UploadedFiles_0-_Part1/andrew@acooke.org_24718989709_tap-sync-18690-effaaaffdd06b9419991471bd92d53d5.fit

class ActivityReader(MultiProcFitReader):

    def __init__(self, *args, constants=None, sport_to_activity=None, record_to_db=None, **kargs):
        self.constants = constants
        self.sport_to_activity = self._assert('sport_to_activity', sport_to_activity)
        self.record_to_db = [(field, name, units, STATISTIC_JOURNAL_CLASSES[type])
                             for field, (name, units, type)
                             in self._assert('record_to_db', record_to_db).items()]
        self.add_elevation = not any(name == ELEVATION for (field, name, units, type) in self.record_to_db)
        self.__ajournal = None  # save for coverage
        super().__init__(*args, **kargs)

    def _base_command(self):
        if self.constants:
            constants = ' '.join(f'-D "{constant}"' for constant in self.constants) + ' -- '
        else:
            constants = ''
        return f'{{ch2}} --{VERBOSITY} 0 --{LOG} {{log}} -f {self.db_path} ' \
               f'{ACTIVITIES} {mm(WORKER)} {self.id} --{FAST} {mm(FORCE) if self.force else ""} {constants}'

    def _startup(self, s):
        super()._startup(s)
        self.__oracle = bilinear_elevation_from_constant(s)

    def _read_data(self, s, file_scan):
        log.info('Reading activity data from %s' % file_scan)
        records = self._read_fit_file(file_scan.path, merge_duplicates, fix_degrees, no_bad_values)
        ajournal, activity_group, first_timestamp = self._create_activity(s, file_scan, records)
        return ajournal, (ajournal, activity_group, first_timestamp, file_scan, records)

    def __read_sport(self, path, records):
        try:
            return self._first(path, records, 'sport').value.sport.lower()
        except AbortImportButMarkScanned:
            # alternative for some garmin devices (florian)
            return self._first(path, records, 'session').value.sport.lower()

    def _create_activity(self, s, file_scan, records):
        first_timestamp = self._first(file_scan, records, 'event', 'record').value.timestamp
        last_timestamp = self._last(file_scan, records, 'event', 'record').value.timestamp
        log.debug(f'Time range: {first_timestamp.timestamp()} - {last_timestamp.timestamp()}')
        sport = self.__read_sport(file_scan, records)
        activity_group = self._activity_group(s, file_scan, sport)
        log.info(f'{activity_group} from {sport}')
        if self.force:
            self._delete_journals(s, activity_group, first_timestamp, last_timestamp)
        else:
            self._check_journals(s, activity_group, first_timestamp, last_timestamp)
        ajournal = add(s, ActivityJournal(activity_group=activity_group,
                                          start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                          file_hash_id=file_scan.file_hash_id))
        return ajournal, activity_group, first_timestamp

    def _activity_group(self, s, file_scan, sport):
        if sport in self.sport_to_activity:
            return self._lookup_activity_group(s, self.sport_to_activity[sport])
        else:
            log.warning('Unrecognised sport: "%s" in %s' % (sport, file_scan))
            if sport in (SPORT_GENERIC,):
                raise Exception(f'Ignoring {sport} entry')
            else:
                raise FatalException(f'There is no group configured for {sport} entries in the FIT file. '
                                     'See sport_to_activity in ch2.config.default.py')

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

    def _delete_journals(self, s, activity_group, first_timestamp, last_timestamp):
        log.debug('Deleting overlapping journals')
        for journal in self._overlapping_journals(s, ActivityJournal, activity_group,
                                                  first_timestamp, last_timestamp).all():
            Timestamp.clear(s, owner=self.owner_out, source=journal)
            log.debug(f'Deleting {journal}')
            s.delete(journal)
        s.commit()

    def _check_journals(self, s, activity_group, first_timestamp, last_timestamp):
        log.debug('Checking for overlapping journals')
        if self._overlapping_journals(s, count(ActivityJournal.id), activity_group,
                                      first_timestamp, last_timestamp).scalar():
            log.warning(f'Overlapping activities for {first_timestamp} - {last_timestamp}')
            raise AbortImportButMarkScanned()

    def _load_constants(self, s, ajournal):
        if self.constants:
            for constant in self.constants:
                name, value = constant.split('=', 1)
                log.debug(f'Setting {name}={value}')
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

        ajournal, activity_group, first_timestamp, file_scan, records = data
        timespan, warned, logged, last_timestamp = None, 0, 0, to_time(0.0)
        self._load_constants(s, ajournal)
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
                            loader.add(name, units, None, activity_group, ajournal, value, timestamp, type)
                            if name == LATITUDE:
                                lat = value
                            elif name == LONGITUDE:
                                lon = value
                    logged += 1
                    # values derived from lat/lon
                    if lat is not None and lon is not None:
                        x, y = Point.from_latitude_longitude(lat, lon).meters
                        loader.add(SPHERICAL_MERCATOR_X, M, None, activity_group, ajournal, x, timestamp,
                                   StatisticJournalFloat)
                        loader.add(SPHERICAL_MERCATOR_Y, M, None, activity_group, ajournal, y, timestamp,
                                   StatisticJournalFloat)
                        if self.add_elevation:
                            elevation = self.__oracle.elevation(lat, lon)
                            if elevation:
                                loader.add(RAW_ELEVATION, M, None, activity_group, ajournal, elevation, timestamp,
                                           StatisticJournalFloat)
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
