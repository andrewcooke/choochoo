
from logging import getLogger

from .climb import add_climb, CLIMB_CNAME
from .database import Counter, add_statistics, add_activity_group, add_activity_constant, add_diary_topic, \
    add_diary_topic_field, \
    add_diary, add_activities, add_monitor, name_constant, add_nearby, add_constant, add_loader_support, \
    add_activity_topic_field
from .impulse import add_impulse, add_responses
from .power import add_power_estimate
from ..diary.model import TYPE, FLOAT, LO, HI, DP, SCORE, EDIT
from ..lib.schedule import Schedule
from ..msil2a.download import MSIL2A_DIR
from ..sql.tables.statistic import StatisticJournalType
from ..sql.tables.topic import DiaryTopicJournal
from ..sql.types import short_cls
from ..srtm.file import SRTM1_DIR
from ..stats.calculate.activity import ActivityCalculator
from ..stats.calculate.elevation import ElevationCalculator
from ..stats.calculate.kit import KitCalculator
from ..stats.calculate.monitor import MonitorCalculator
from ..stats.calculate.response import ResponseCalculator
from ..stats.calculate.segment import SegmentCalculator
from ..stats.calculate.summary import SummaryCalculator
from ..stats.display.activity import ActivityDiary
from ..stats.display.monitor import MonitorDiary
from ..stats.display.nearby import NearbyDiary
from ..stats.display.response import ResponseDiary
from ..stats.display.segment import SegmentDiary
from ..stats.names import BPM, FTHR, LONGITUDE, LATITUDE, HEART_RATE, SPEED, DISTANCE, ALTITUDE, DEG, MS, M, CADENCE, \
    RPM, FITNESS_D, FATIGUE_D, ALL, SPORT_WALKING, SPORT_SWIMMING, SPORT_RUNNING, SPORT_CYCLING, KM
from ..stats.read.monitor import MonitorReader
from ..stats.read.segment import SegmentReader

log = getLogger(__name__)


def default(system, db, no_diary=False):

    with db.session_context() as s:

        # the following uses helper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        add_loader_support(s)

        # basic activities

        c = Counter()
        # each of the following needs an FTHR defined
        bike = add_activity_group(s, 'Bike', c, description='All cycling activities')
        run = add_activity_group(s, 'Run', c, description='All running activities')
        swim = add_activity_group(s, 'Swim', c, description='All swimming activities')
        walk = add_activity_group(s, 'Walk', c, description='All walking activities')
        # this is required by the code; the name (ALL) is fixed and referenced in FF calculations
        all = add_activity_group(s, ALL, c, description='All activities')
        # sport_to_activity maps from the FIT sport field to the activity defined above
        sport_to_activity = {SPORT_CYCLING: bike.name,
                             SPORT_RUNNING: run.name,
                             SPORT_SWIMMING: swim.name,
                             SPORT_WALKING: walk.name}
        add_activities(s, SegmentReader, c,
                       owner_out=short_cls(SegmentReader),
                       sport_to_activity=sport_to_activity,
                       # todo - does this need to depend on activity group?
                       record_to_db={'position_lat': (LATITUDE, DEG, StatisticJournalType.FLOAT),
                                     'position_long': (LONGITUDE, DEG, StatisticJournalType.FLOAT),
                                     'heart_rate': (HEART_RATE, BPM, StatisticJournalType.INTEGER),
                                     'enhanced_speed': (SPEED, MS, StatisticJournalType.FLOAT),
                                     'distance': (DISTANCE, KM, StatisticJournalType.FLOAT),
                                     'enhanced_altitude': (ALTITUDE, M, StatisticJournalType.FLOAT),
                                     'cadence': (CADENCE, RPM, StatisticJournalType.INTEGER)})

        # statistics pipeline (called to calculate missing statistics)

        # FF-model parameters
        # 7 and 42 days as for training peaks
        # https://www.trainingpeaks.com/blog/the-science-of-the-performance-manager/
        # you can add further values as determined from your own data
        # https://andrewcooke.github.io/choochoo/ff-fitting
        fitness = ((42, 1, 1),)
        fatigue = ((7, 1, 5),)

        c = Counter()
        add_statistics(s, ElevationCalculator, c, owner_in='[unused - data via activity_statistics]')
        add_power_estimate(s, c, bike, vary='')
        add_climb(s, bike)
        add_impulse(s, c, bike)
        add_impulse(s, c, walk)
        add_responses(s, c, fitness=fitness, fatigue=fatigue)
        add_statistics(s, ActivityCalculator, c,
                       owner_in=short_cls(ResponseCalculator),
                       climb=name_constant(CLIMB_CNAME, bike))
        add_statistics(s, SegmentCalculator, c, owner_in=short_cls(SegmentReader))
        add_statistics(s, MonitorCalculator, c, owner_in=short_cls(MonitorReader))
        add_statistics(s, KitCalculator, c, owner_in=short_cls(SegmentReader))

        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        # also, add year first so that monthly doesn't get confused by extra stats range
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('x'))
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('y'))
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('m'))

        # obviously you need to edit these parameters - see `ch2 constants show Nearby.Bike`
        add_nearby(s, c, bike, 'Santiago', -33.4, -70.4, fraction=0.1, border=150)
        add_nearby(s, c, walk, 'Santiago', -33.4, -70.4, fraction=0.1, border=150)

        # diary pipeline (called to display data in the diary)

        c = Counter()
        add_diary(s, MonitorDiary, c)
        # these tie-in to the constants used in add_impulse()
        add_diary(s, ResponseDiary, c,
                  fitness=[name_constant(FITNESS_D % days, all) for (days, _, _) in fitness],
                  fatigue=[name_constant(FATIGUE_D % days, all) for (days, _, _) in fatigue])
        add_diary(s, ActivityDiary, c)
        add_diary(s, SegmentDiary, c)
        add_diary(s, NearbyDiary, c)

        # monitor pipeline

        c = Counter()
        add_monitor(s, MonitorReader, c, sport_to_activity=sport_to_activity)

        # constants used by statistics

        add_activity_constant(s, bike, FTHR,
                              description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, run, FTHR,
                              description='Heart rate at functional threshold (running).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, swim, FTHR,
                              description='Heart rate at functional threshold (swimming).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, walk, FTHR,
                              description='Heart rate at functional threshold (walking).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_constant(s, SRTM1_DIR, description='Directory containing STRM1 hgt files for elevations (see http://dwtkns.com/srtm30m)',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)
        add_constant(s, MSIL2A_DIR, description='Directory containing Sentinel 2A imaging data (see https://scihub.copernicus.eu/dhus/#/home)',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)

        if not no_diary:

            # a basic diary

            c = Counter()
            diary = add_diary_topic(s, 'Diary', c)
            add_diary_topic_field(s, diary, 'Notes', c, StatisticJournalType.TEXT,
                                  model={TYPE: EDIT})
            add_diary_topic_field(s, diary, 'Weight', c, StatisticJournalType.FLOAT,
                                  units='kg', summary='[avg],[msr]',
                                  model={TYPE: FLOAT, LO: 50, HI: 100, DP: 1})
            add_diary_topic_field(s, diary, 'Sleep', c, StatisticJournalType.FLOAT,
                                  units='h', summary='[avg]',
                                  model={TYPE: FLOAT, LO: 0, HI: 24, DP: 1})
            add_diary_topic_field(s, diary, 'Mood', c, StatisticJournalType.FLOAT,
                                  summary='[avg]',
                                  model={TYPE: SCORE})
            add_diary_topic_field(s, diary, 'Nutrition', c, StatisticJournalType.TEXT,
                                  summary='[cnt]',
                                  model={TYPE: EDIT})
            add_diary_topic_field(s, diary, 'Soreness', c, StatisticJournalType.TEXT,
                                  summary='[cnt]',
                                  model={TYPE: EDIT})
            add_diary_topic_field(s, diary, 'Medication', c, StatisticJournalType.TEXT,
                                  summary='[cnt]',
                                  model={TYPE: EDIT})
            add_diary_topic_field(s, diary, 'Weather', c, StatisticJournalType.TEXT,
                                  summary='[cnt]',
                                  model={TYPE: EDIT})
            add_diary_topic_field(s, diary, 'Route', c, StatisticJournalType.TEXT,
                                  summary='[cnt]',
                                  model={TYPE: EDIT})

            # and activity-related topics
            # a null parent here means that the fields appear under the title

            for activity_group in (bike, run, swim, walk):
                c = Counter()
                if activity_group != swim:
                    add_activity_topic_field(s, None, 'Route', c, StatisticJournalType.TEXT,
                                             activity_group, model={TYPE: EDIT})
                add_activity_topic_field(s, None, 'Notes', c, StatisticJournalType.TEXT,
                                         activity_group, model={TYPE: EDIT})

        # finally, set the TZ so that first use of the diary doesn't wipe all our intervals
        DiaryTopicJournal.check_tz(system, s)
