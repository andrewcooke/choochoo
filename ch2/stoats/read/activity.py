
from logging import getLogger
from os.path import splitext, basename

from pygeotile.point import Point

from ch2.squeal.utils import add
from ..load import StatisticJournalLoader
from ..names import LATITUDE, LONGITUDE, M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, ELEVATION, RAW_ELEVATION
from ..read import AbortImport, MultiProcFitReader
from ...commands.args import ACTIVITIES, WORKER, FAST, mm, FORCE, parse_pairs
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...lib.date import to_time
from ...sortem.bilinear import bilinear_elevation_from_constant
from ...squeal.database import Timestamp, StatisticJournalText
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES

log = getLogger(__name__)


class ActivityReader(MultiProcFitReader):

    def __init__(self, *args, cost_calc=4, cost_write=1, constants=None, sport_to_activity=None, record_to_db=None,
                 **kargs):
        self.constants = constants
        self.sport_to_activity = self._assert('sport_to_activity', sport_to_activity)
        self.record_to_db = [(field, name, units, STATISTIC_JOURNAL_CLASSES[type])
                             for field, (name, units, type)
                             in self._assert('record_to_db', record_to_db).items()]
        self.add_elevation = not any(name == ELEVATION for (field, name, units, type) in self.record_to_db)
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _base_command(self):
        if self.constants:
            constants = ' '.join(f'-D "{constant}"' for constant in self.constants) + ' -- '
        else:
            constants = ''
        return f'{{ch2}} -v0 -l {{log}} {ACTIVITIES} {mm(WORKER)} {self.id} ' \
            f'{mm(FAST)} {mm(FORCE) if self.force else ""} {constants}'

    def _startup(self, s):
        super()._startup(s)
        self.__oracle = bilinear_elevation_from_constant(log, s)

    def _read(self, s, path):

        log.info('Reading activity data from %s' % path)

        records = self._load_fit_file(path, merge_duplicates, fix_degrees, no_bad_values)
        ajournal, activity_group, first_timestamp = self._create_activity(s, path, records)
        self._load_constants(s, ajournal)
        s.commit()  # allow other workers in

        loader = StatisticJournalLoader(s, self.owner_out)
        timespan, warned, last_timestamp = None, 0, to_time(0.0)

        # used by nearby calculations to avoid work
        # no need for constraint because ajournal is per-group
        # use this class so import itself is always clearly understood, even if the subclass changes.
        with Timestamp(owner=self.owner_out, key=ajournal.id).on_success(log, s):

            for record in records:
                if record.name == 'event' or (record.name == 'record' and record.timestamp > last_timestamp):
                    if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                        if timespan:
                            log.warning('Ignoring start with no corresponding stop (possible lost data?)')
                        else:
                            timespan = add(s, ActivityTimespan(activity_journal=ajournal,
                                                               start=record.value.timestamp,
                                                               finish=record.value.timestamp))
                    if record.name == 'record':
                        lat, lon, timestamp = None, None, record.value.timestamp
                        # customizable loader
                        for field, name, units, type in self.record_to_db:
                            value = record.data.get(field, None)
                            if value is not None:
                                value = value[0][0]
                                loader.add(name, units, None, activity_group, ajournal, value, timestamp, type)
                                if name == LATITUDE:
                                    lat = value
                                elif name == LONGITUDE:
                                    lon = value
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
                    if record.name == 'event' and record.value.event == 'timer' \
                            and record.value.event_type == 'stop_all':
                        if timespan:
                            timespan.finish = record.value.timestamp
                            ajournal.finish = record.value.timestamp
                            timespan = None
                        else:
                            log.debug('Ignoring stop with no corresponding start (possible lost data?)')
                    if record.name == 'record':
                        last_timestamp = record.timestamp
                else:
                    if record.name == 'record':
                        log.warning('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                          (path, record.timestamp))

            loader.load()

        s.commit()  # allow other workers in

        # used by subclasses
        return ajournal, loader

    def _create_activity(self, s, path, records):
        first_timestamp = self._first(path, records, 'event', 'record').value.timestamp
        sport = self._first(path, records, 'sport').value.sport.lower()
        activity_group = self._activity_group(s, path, sport)
        self._delete_journals(s, activity_group, first_timestamp)
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

    def _delete_journals(self, s, activity_group, first_timestamp):
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for journal in s.query(ActivityJournal). \
                filter(ActivityJournal.activity_group == activity_group,
                       ActivityJournal.start == first_timestamp).all():
            Timestamp.clear(s, owner=self.owner_out, key=journal.id)
            s.delete(journal)
        s.flush()

    def _load_constants(self, s, ajournal):
        if self.constants:
            for constant in self.constants:
                name, value = constant.split('=', 1)
                log.debug(f'Setting {name}={value}')
                StatisticJournalText.add(log, s, name, None, None, self.owner_out, ajournal.activity_group,
                                         ajournal, value, ajournal.start)
