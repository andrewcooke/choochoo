
from os.path import splitext, basename

from ..read import AbortImport
from ...fit.format.read import filtered_records
from ...fit.format.records import fix_degrees
from ...lib.date import to_time
from ...lib.utils import datetime_to_epoch
from ...squeal.database import add
from ...squeal.tables.activity import ActivityGroup, ActivityJournal, ActivityTimespan
from ...squeal.tables.statistic import StatisticJournalFloat, StatisticJournalInteger, StatisticJournal, \
    STATISTIC_JOURNAL_CLASSES
from ...stoats.names import LATITUDE, DEG, LONGITUDE, HEART_RATE, DISTANCE, KMH, SPEED, BPM, M
from ...stoats.read import Importer

ActivityWaypoint = None


class ActivityImporter(Importer):

    def __init__(self, log, db):
        super().__init__(log, db)
        self.__statistics_cache = {}

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
        journal = add(s, ActivityJournal(activity_group=activity_group,
                                         start=first_timestamp, finish=first_timestamp,  # will be over-written later
                                         fit_file=path, name=splitext(basename(path))[0]))

        timespan, warned, latest = None, 0, to_time(0.0)
        self._log.info('Loading data for activity')
        for record in records:
            if record.name == 'event' or (record.name == 'record' and record.timestamp > latest):
                if record.name == 'event' and record.value.event == 'timer' and record.value.event_type == 'start':
                    timespan = add(s, ActivityTimespan(activity_journal=journal,
                                                       start=record.value.timestamp, finish=record.value.timestamp))
                if record.name == 'record':
                    self._add(s, LATITUDE, DEG, None, self, activity_group.id, journal,
                              record.none.position_lat, record.value.timestamp, StatisticJournalFloat)
                    self._add(s, LONGITUDE, DEG, None, self, activity_group.id, journal,
                              record.none.position_long, record.value.timestamp,
                              StatisticJournalFloat)
                    self._add(s, HEART_RATE, BPM, None, self, activity_group.id, journal,
                              record.none.heart_rate, record.value.timestamp, StatisticJournalInteger)
                    self._add(s, DISTANCE, M, None, self, activity_group.id, journal,
                              record.none.distance, record.value.timestamp, StatisticJournalFloat)
                    self._add(s, SPEED, KMH, None, self, activity_group.id, journal,
                              record.none.enhanced_speed, record.value.timestamp, StatisticJournalFloat)
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
                                   (path, record.timestamp))
            # except (AttributeError, TypeError) as e:
            #     if warned < 10:
            #         self._log.warn('Error while reading %s - some data may be missing (%s)' % (path, e))
            #     elif warned == 10:
            #         self._log.warn('No more warnings will be given for %s' % path)
            #     warned += 1

    def _add(self, s, name, units, summary, owner, constraint, source, value, time, type):
        # cache statistic_name instances for speed (avoid flush on each query)
        if name not in self.__statistics_cache:
            self.__statistics_cache[name] = \
                StatisticJournal.add_name(self._log, s, name, units, summary, owner, constraint)
        statistic_name = self.__statistics_cache[name]
        add(s, type(statistic_name=statistic_name, source=source, value=value, time=time))
