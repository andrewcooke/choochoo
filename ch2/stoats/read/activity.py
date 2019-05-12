
from logging import getLogger
from os.path import splitext, basename

from pygeotile.point import Point
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import count

from ..names import LATITUDE, LONGITUDE, M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, ELEVATION, RAW_ELEVATION
from ..read import AbortImport, MultiProcFitReader, AbortImportButMarkScanned
from ...commands.args import ACTIVITIES, WORKER, FAST, mm, FORCE
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...lib.date import to_time
from ...sortem.bilinear import bilinear_elevation_from_constant
from ...squeal.database import Timestamp, StatisticJournalText
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES
from ...squeal.utils import add

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
        super().__init__(*args, **kargs)

    def _base_command(self):
        if self.constants:
            constants = ' '.join(f'-D "{constant}"' for constant in self.constants) + ' -- '
        else:
            constants = ''
        return f'{{ch2}} -v0 -l {{log}} -f {self._db.path} {ACTIVITIES} {mm(WORKER)} {self.id} ' \
            f'{mm(FAST)} {mm(FORCE) if self.force else ""} {constants}'

    def _startup(self, s):
        super()._startup(s)
        self.__oracle = bilinear_elevation_from_constant(log, s)

    def _read_data(self, s, path):
        log.info('Reading activity data from %s' % path)
        records = self._read_fit_file(path, merge_duplicates, fix_degrees, no_bad_values)
        ajournal, activity_group, first_timestamp = self._create_activity(s, path, records)
        self._load_constants(s, ajournal)
        return ajournal.id, (ajournal, activity_group, first_timestamp, path, records)

    def __read_sport(self, path, records):
        try:
            return self._first(path, records, 'sport').value.sport.lower()
        except AbortImportButMarkScanned:
            # alternative for some garmin devices (florian)
            return self._first(path, records, 'session').value.sport.lower()

    def _create_activity(self, s, path, records):
        first_timestamp = self._first(path, records, 'event', 'record').value.timestamp
        last_timestamp = self._last(path, records, 'event', 'record').value.timestamp
        log.debug(f'Time range: {first_timestamp.timestamp()} - {last_timestamp.timestamp()}')
        sport = self.__read_sport(path, records)
        activity_group = self._activity_group(s, path, sport)
        log.info(f'{activity_group} from {sport}')
        if self.force:
            self._delete_journals(s, activity_group, first_timestamp, last_timestamp)
        else:
            self._check_journals(s, activity_group, first_timestamp, last_timestamp)
        ajournal = add(s, ActivityJournal(activity_group=activity_group,
                                          start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                          fit_file=path, name=splitext(basename(path))[0]))
        return ajournal, activity_group, first_timestamp

    def _activity_group(self, s, path, sport):
        if sport in self.sport_to_activity:
            return self._lookup_activity_group(s, self.sport_to_activity[sport])
        else:
            log.warning('Unrecognised sport: "%s" in %s' % (sport, path))
            raise AbortImport()

    def _lookup_activity_group(self, s, name):
        activity_group = s.query(ActivityGroup).filter(ActivityGroup.name == name).one_or_none()
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
        for journal in self._overlapping_journals(s, ActivityJournal, activity_group,
                                                  first_timestamp, last_timestamp).all():
            Timestamp.clear(s, owner=self.owner_out, key=journal.id)
            log.debug(f'Deleting {journal}')
            s.delete(journal)
        s.commit()

    def _check_journals(self, s, activity_group, first_timestamp, last_timestamp):
        if self._overlapping_journals(s, count(ActivityJournal.id), activity_group,
                                      first_timestamp, last_timestamp).scalar():
            log.warning(f'Overlapping activities for {first_timestamp} - {last_timestamp}')
            raise AbortImportButMarkScanned()

    def _load_constants(self, s, ajournal):
        if self.constants:
            for constant in self.constants:
                name, value = constant.split('=', 1)
                log.debug(f'Setting {name}={value}')
                StatisticJournalText.add(log, s, name, None, None, self.owner_out, ajournal.activity_group,
                                         ajournal, value, ajournal.start)

    def _load_data(self, s, loader, data):

        ajournal, activity_group, first_timestamp, path, records = data
        timespan, warned, logged, last_timestamp = None, 0, 0, to_time(0.0)
        log.debug(f'Loading {self.record_to_db}')

        def is_event(record, *types):
            # return record.name == 'event' and record.value.event == 'timer' and record.value.event_type == type
            # iphone does things differently..
            return record.name == 'event' and record.value.event_type in types

        have_timespan = any(is_event(record, 'start') for record in records)
        if not have_timespan:
            log.warning('Experimental handling of data without timespans')
            final_timestamp = filter(lambda x: x.name == 'record', records)[-1].timestamp
            timespan = add(s, ActivityTimespan(activity_journal=ajournal,
                                               start=first_timestamp,
                                               finish=final_timestamp))

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
                                (path, record.value.timestamp))
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

