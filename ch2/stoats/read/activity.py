
from os.path import splitext, basename

from pygeotile.point import Point

from ..load import StatisticJournalLoader
from ..names import LATITUDE, DEG, LONGITUDE, HEART_RATE, DISTANCE, KMH, SPEED, BPM, M, SPHERICAL_MERCATOR_X, \
    SPHERICAL_MERCATOR_Y
from ..read import AbortImport, Importer
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees
from ...lib.date import to_time
from ...squeal.database import add
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournalFloat, StatisticJournalInteger


class ActivityImporter(Importer):

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
        loader = StatisticJournalLoader(self._log, s, self)

        data, types, messages, records = filtered_records(self._log, path)
        records = [record.force(fix_degrees)
                   for record in sorted(records, key=lambda r: r.timestamp if r.timestamp else to_time(0.0))]

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
                    loader.add(LATITUDE, DEG, None, activity_group, ajournal,
                              record.none.position_lat, record.value.timestamp, StatisticJournalFloat)
                    loader.add(LONGITUDE, DEG, None, activity_group, ajournal,
                              record.none.position_long, record.value.timestamp,
                              StatisticJournalFloat)
                    if record.none.position_lat and record.none.position_long:
                        p = Point.from_latitude_longitude(record.none.position_lat, record.none.position_long)
                        x, y = p.meters
                        loader.add(SPHERICAL_MERCATOR_X, M, None, activity_group, ajournal,
                                  x, record.value.timestamp, StatisticJournalFloat)
                        loader.add(SPHERICAL_MERCATOR_Y, M, None, activity_group, ajournal,
                                  y, record.value.timestamp, StatisticJournalFloat)
                    loader.add(HEART_RATE, BPM, None, activity_group, ajournal,
                              record.none.heart_rate, record.value.timestamp, StatisticJournalInteger)
                    loader.add(DISTANCE, M, None, activity_group, ajournal,
                              record.none.distance, record.value.timestamp, StatisticJournalFloat)
                    loader.add(SPEED, KMH, None, activity_group, ajournal,
                              record.none.enhanced_speed, record.value.timestamp, StatisticJournalFloat)
                if record.name == 'event' and record.value.event == 'timer' \
                        and record.value.event_type == 'stop_all':
                    if timespan:
                        timespan.finish = record.value.timestamp
                        ajournal.finish = record.value.timestamp
                        timespan = None
                    else:
                        self._log.warning('Ignoring stop with no corresponding start (possible lost data?)')
                if record.name == 'record':
                    last_timestamp = record.timestamp
            else:
                if record.name == 'record':
                    self._log.warning('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                   (path, record.timestamp))

        loader.load()

        # manually clean out intervals because we're doing a stealth load
        Interval.clean_times(s, first_timestamp, last_timestamp)

        # used by subclasses
        return ajournal, loader

