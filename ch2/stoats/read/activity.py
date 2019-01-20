
from os.path import splitext, basename

from pygeotile.point import Point

from ..load import StatisticJournalLoader
from ..names import LATITUDE, LONGITUDE, M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, ELEVATION
from ..read import AbortImport, Importer
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees, merge_duplicates, no_bad_values
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...sortem import oracle_from_constant
from ...squeal.database import add
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournalFloat, STATISTIC_JOURNAL_CLASSES


class ActivityImporter(Importer):

    def _on_init(self, *args, **kargs):
        super()._on_init(*args, **kargs)
        with self._db.session_context() as s:
            self.__oracle = oracle_from_constant(self._log, s)

    def run(self, paths, force=False):
        if 'sport_to_activity' not in self._kargs:
            raise Exception('No map from sport to activity')
        self._run(paths, force=force)

    def _activity_group(self, s, path, sport, sport_to_activity):
        if sport in sport_to_activity:
            return self._lookup_activity_group(s, sport_to_activity[sport])
        else:
            self._log.warning('Unrecognised sport: "%s" in %s' % (sport, path))
            raise AbortImport()

    def _lookup_activity_group(self, s, name):
        activity_group = s.query(ActivityGroup).filter(ActivityGroup.name == name).one_or_none()
        if not activity_group:
            activities = s.query(ActivityGroup).all()
            if activities:
                self._log.info('Available activity group:')
                for activity_group in activities:
                    self._log.info('%s - %s' % (activity_group.name, activity_group.description))
            else:
                self._log.error('No activity groups defined - configure system correctly')
            raise Exception('ActivityGroup "%s" is not defined' % name)
        return activity_group

    def _delete_journals(self, s, activity_group, first_timestamp):
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for journal in s.query(ActivityJournal). \
                filter(ActivityJournal.activity_group == activity_group,
                       ActivityJournal.start == first_timestamp).all():
            s.delete(journal)
        s.flush()

    def _import(self, s, path):

        sport_to_activity = self._assert_karg('sport_to_activity')
        record_to_db = [(field, name, units, STATISTIC_JOURNAL_CLASSES[type])
                        for field, (name, units, type) in self._assert_karg('record_to_db').items()]
        add_elevation = not any(name == ELEVATION for (field, name, units, type) in record_to_db)
        loader = StatisticJournalLoader(self._log, s, self)

        types, messages, records = filtered_records(self._log, read_fit(self._log, path))
        records = [record.as_dict(merge_duplicates, fix_degrees, no_bad_values)
                   for _, _, record in sorted(records,
                                              key=lambda r: r[2].timestamp if r[2].timestamp else to_time(0.0))]

        first_timestamp = self._first(path, records, 'event', 'record').value.timestamp
        sport = self._first(path, records, 'sport').value.sport.lower()
        activity_group = self._activity_group(s, path, sport, sport_to_activity)
        self._delete_journals(s, activity_group, first_timestamp)
        ajournal = add(s, ActivityJournal(activity_group=activity_group,
                                          start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                          fit_file=path, name=splitext(basename(path))[0]))

        timespan, warned, last_timestamp = None, 0, to_time(0.0)
        self._log.info('Importing activity data from %s' % path)
        for record in records:
            if record.name == 'event' or (record.name == 'record' and record.timestamp > last_timestamp):
                if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                    if timespan:
                        self._log.warning('Ignoring start with no corresponding stop (possible lost data?)')
                    else:
                        timespan = add(s, ActivityTimespan(activity_journal=ajournal,
                                                           start=record.value.timestamp,
                                                           finish=record.value.timestamp))
                if record.name == 'record':
                    lat, lon, timestamp = None, None, record.value.timestamp
                    # customizable loader
                    for field, name, units, type in record_to_db:
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
                        if add_elevation:
                            elevation = self.__oracle.elevation(lat, lon)
                            if elevation:
                                loader.add(ELEVATION, M, None, activity_group, ajournal, elevation, timestamp,
                                           StatisticJournalFloat)
                if record.name == 'event' and record.value.event == 'timer' \
                        and record.value.event_type == 'stop_all':
                    if timespan:
                        timespan.finish = record.value.timestamp
                        ajournal.finish = record.value.timestamp
                        timespan = None
                    else:
                        self._log.debug('Ignoring stop with no corresponding start (possible lost data?)')
                if record.name == 'record':
                    last_timestamp = record.timestamp
            else:
                if record.name == 'record':
                    self._log.warning('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                   (path, record.timestamp))

        loader.load()

        # manually clean out intervals because we're doing a fast load
        Interval.clean_times(s, first_timestamp, last_timestamp)

        # used by subclasses
        return ajournal, loader

