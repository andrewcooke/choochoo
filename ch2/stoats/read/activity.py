
from collections import defaultdict
from os.path import splitext, basename

from sqlalchemy import func
from pygeotile.point import Point

from ..read import AbortImport
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees
from ...lib.date import to_time
from ...squeal.database import add
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.statistic import StatisticJournalFloat, StatisticJournalInteger, StatisticJournal, StatisticName
from ...stoats.names import LATITUDE, DEG, LONGITUDE, HEART_RATE, DISTANCE, KMH, SPEED, BPM, M, SPHERICAL_MERCATOR_X, \
    SPHERICAL_MERCATOR_Y
from ...stoats.read import Importer


class ActivityImporter(Importer):

    def __init__(self, log, db):
        super().__init__(log, db)
        self.__staging = defaultdict(lambda: [])

    def run(self, paths, force=False, sport_to_activity=None):
        if sport_to_activity is None:
            raise Exception('No map from sport to activity')
        self._run(paths, force=force, sport_to_activity=sport_to_activity)

    def _activity_group(self, s, path, sport, sport_to_activity):
        if sport in sport_to_activity:
            return self._lookup_activity_group(s, sport_to_activity[sport])
        else:
            self._log.warn('Unrecognised sport: "%s" in %s' % (sport, path))
            raise AbortImport()

    def _lookup_activity_group(self, s, name):
        activity_group = s.query(ActivityGroup).filter(ActivityGroup.name == name).one_or_none()
        if not activity_group:
            activities = s.query(ActivityGroup).all()
            if activities:
                self._log.info('Available activities:')
                for activity_group in activities:
                    self._log.info('%s - %s' % (activity_group.name, activity_group.description))
            else:
                self._log.error('No activities defined - configure system correctly')
            raise Exception('ActivityGroup "%s" is not defined' % name)
        return activity_group

    def _delete_journals(self, s, activity_group, first_timestamp):
        # need to iterate because sqlite doesn't support multi-table delete and we have inheritance.
        for journal in s.query(ActivityJournal). \
                filter(ActivityJournal.activity_group == activity_group,
                       ActivityJournal.start == first_timestamp).all():
            s.delete(journal)
        s.flush()

    def _import(self, s, path, sport_to_activity):

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

        timespan, warned, latest = None, 0, to_time(0.0)
        self._log.info('Importing activity data from %s' % path)
        for record in records:
            if record.name == 'event' or (record.name == 'record' and record.timestamp > latest):
                if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                    if timespan:
                        self._log.warn('Ignoring start with no corresponding stop (possible lost data?)')
                    else:
                        timespan = add(s, ActivityTimespan(activity_journal=ajournal,
                                                           start=record.value.timestamp,
                                                           finish=record.value.timestamp))
                if record.name == 'record':
                    self._add(s, LATITUDE, DEG, None, self, activity_group, ajournal,
                              record.none.position_lat, record.value.timestamp, StatisticJournalFloat)
                    self._add(s, LONGITUDE, DEG, None, self, activity_group, ajournal,
                              record.none.position_long, record.value.timestamp,
                              StatisticJournalFloat)
                    if record.none.position_lat and record.none.position_long:
                        p = Point.from_latitude_longitude(record.none.position_lat, record.none.position_long)
                        x, y = p.meters
                        self._add(s, SPHERICAL_MERCATOR_X, M, None, self, activity_group, ajournal,
                                  x, record.value.timestamp, StatisticJournalFloat)
                        self._add(s, SPHERICAL_MERCATOR_Y, M, None, self, activity_group, ajournal,
                                  y, record.value.timestamp, StatisticJournalFloat)
                    self._add(s, HEART_RATE, BPM, None, self, activity_group, ajournal,
                              record.none.heart_rate, record.value.timestamp, StatisticJournalInteger)
                    self._add(s, DISTANCE, M, None, self, activity_group, ajournal,
                              record.none.distance, record.value.timestamp, StatisticJournalFloat)
                    self._add(s, SPEED, KMH, None, self, activity_group, ajournal,
                              record.none.enhanced_speed, record.value.timestamp, StatisticJournalFloat)
                if record.name == 'event' and record.value.event == 'timer' \
                        and record.value.event_type == 'stop_all':
                    if timespan:
                        timespan.finish = record.value.timestamp
                        ajournal.finish = record.value.timestamp
                        timespan = None
                    else:
                        self._log.warn('Ignoring stop with no corresponding start (possible lost data?)')
                if record.name == 'record':
                    latest = record.timestamp
            else:
                if record.name == 'record':
                    self._log.warn('Ignoring duplicate record data for %s at %s - some data may be missing' %
                                   (path, record.timestamp))

        self._load(s, ajournal)

    def _load(self, s, ajournal):

        s.flush()
        s.commit()

        names = dict((name, s.query(StatisticName.id).
                      filter(StatisticName.name == name,
                             StatisticName.owner == self).scalar())
                     for name in (LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                  HEART_RATE, DISTANCE, SPEED))

        rowid = s.query(func.max(StatisticJournal.id)).scalar() + 1

        for type in self.__staging:
            for sjournal in self.__staging[type]:
                sjournal.id = rowid
                name = sjournal.statistic_name.name
                sjournal.statistic_name = None
                sjournal.statistic_name_id = names[name]
                sjournal.source = None
                sjournal.source_id = ajournal.id
                rowid += 1
            s.bulk_save_objects(self.__staging[type])

    def _add(self, s, name, units, summary, owner, constraint, source, value, time, type):
        self.__staging[type].append(self._create(s, name, units, summary, owner, constraint, source, value, time, type))
