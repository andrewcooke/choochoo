from logging import getLogger

from .climb import add_climb, CLIMB_CNAME
from .database import Counter, add_statistics, add_activity_group, add_activity_constant, add_topic, add_topic_field, \
    add_diary, add_activities, add_monitor, name_constant, add_nearby, add_constant, add_loader_support
from .impulse import add_impulse
from .power import add_power_estimate
from ..lib.schedule import Schedule
from ..sortem.file import SRTM1_DIR
from ..squeal.tables.statistic import StatisticJournalType
from ..squeal.tables.topic import TopicJournal
from ..squeal.types import short_cls
from ..stoats.calculate.activity import ActivityCalculator
from ..stoats.calculate.elevation import ElevationCalculator
from ..stoats.calculate.monitor import MonitorCalculator
from ..stoats.calculate.power import PowerCalculator
from ..stoats.calculate.segment import SegmentCalculator
from ..stoats.calculate.summary import SummaryCalculator
from ..stoats.display.activity import ActivityDiary
from ..stoats.display.impulse import ImpulseDiary
from ..stoats.display.monitor import MonitorDiary
from ..stoats.display.nearby import NearbyDiary
from ..stoats.display.segment import SegmentDiary
from ..stoats.names import BPM, FTHR, LONGITUDE, LATITUDE, HEART_RATE, SPEED, DISTANCE, ALTITUDE, DEG, MS, M, CADENCE, \
    RPM, FITNESS_D, FATIGUE_D
from ..stoats.read.monitor import MonitorReader
from ..stoats.read.segment import SegmentReader
from ..uweird.fields.topic import Text, Float, Score0

log = getLogger(__name__)


def default(db, no_diary=False):

    with db.session_context() as s:

        # the following users helper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        add_loader_support(s)

        # basic activities

        c = Counter()
        bike = add_activity_group(s, 'Bike', c, description='All cycling activities')
        run = add_activity_group(s, 'Run', c, description='All running activities')
        # sport_to_activity maps from the FIT sport field to the activity defined above
        add_activities(s, SegmentReader, c,
                       owner_out=short_cls(SegmentReader),
                       sport_to_activity={'cycling': bike.name, 'running': run.name},
                       record_to_db={'position_lat': (LATITUDE, DEG, StatisticJournalType.FLOAT),
                                     'position_long': (LONGITUDE, DEG, StatisticJournalType.FLOAT),
                                     'heart_rate': (HEART_RATE, BPM, StatisticJournalType.INTEGER),
                                     'enhanced_speed': (SPEED, MS, StatisticJournalType.FLOAT),
                                     'distance': (DISTANCE, M, StatisticJournalType.FLOAT),
                                     'enhanced_altitude': (ALTITUDE, M, StatisticJournalType.FLOAT),
                                     'cadence': (CADENCE, RPM, StatisticJournalType.INTEGER)})

        # statistics pipeline (called to calculate missing statistics)

        # FF-model parameters
        # 7 and 42 days as for training peaks
        # https://www.trainingpeaks.com/blog/the-science-of-the-performance-manager/
        fitness=((42, 1), (260, 1/6))
        fatigue=((7, 5),)

        c = Counter()
        add_statistics(s, ElevationCalculator, c, owner_in='[unused - data via activity_statistics]')
        add_power_estimate(s, c, bike, vary='')
        add_climb(s, bike)
        add_impulse(s, c, bike, fitness=fitness, fatigue=fatigue)
        add_statistics(s, ActivityCalculator, c,
                       owner_in=f'{short_cls(SegmentReader)},{short_cls(PowerCalculator)},{short_cls(ElevationCalculator)}',
                       climb=name_constant(CLIMB_CNAME, bike))
        add_statistics(s, SegmentCalculator, c, owner_in=short_cls(SegmentReader))
        add_statistics(s, MonitorCalculator, c, owner_in=short_cls(MonitorReader))

        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        # also, add year first so that monthly doesn't get confused by extra stats range
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('y'))
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('m'))

        # obviously you need to edit these parameters - see `ch2 constants Nearby.Bike`
        add_nearby(s, c, bike, 'Santiago', -33.4, -70.4, fraction=0.1, border=150)

        # diary pipeline (called to display data in the diary)

        c = Counter()
        add_diary(s, MonitorDiary, c)
        # these tie-in to the constants used in add_impulse()
        add_diary(s, ImpulseDiary, c,
                  fitness=[name_constant(FITNESS_D % days, bike) for (days, _) in fitness],
                  fatigue=[name_constant(FATIGUE_D % days, bike) for (days, _) in fatigue])
        add_diary(s, ActivityDiary, c)
        add_diary(s, SegmentDiary, c)
        add_diary(s, NearbyDiary, c)

        # monitor pipeline

        c = Counter()
        add_monitor(s, MonitorReader, c)

        # constants used by statistics

        add_activity_constant(s, bike, FTHR,
                              description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, run, FTHR,
                              description='Heart rate at functional threshold (running).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_constant(s, SRTM1_DIR, description='Directory containing STRM1 hgt files for elevations (see http://dwtkns.com/srtm30m)',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)

        if not no_diary:

            # a basic diary

            c = Counter()
            diary = add_topic(s, 'Diary', c)
            add_topic_field(s, diary, 'Notes', c, StatisticJournalType.TEXT,
                            display_cls=Text)
            # now provided via monitor
            # add_topic_field(s, diary, 'Rest HR', c,
            #                 units=BPM, summary='[avg]',
            #                 display_cls=Integer, lo=25, hi=75)
            add_topic_field(s, diary, 'Weight', c, StatisticJournalType.FLOAT,
                            units='kg', summary='[avg],[msr]',
                            display_cls=Float, lo=50, hi=100, dp=1)
            add_topic_field(s, diary, 'Sleep', c, StatisticJournalType.FLOAT,
                            units='h', summary='[avg]',
                            display_cls=Float, lo=0, hi=24, dp=1)
            add_topic_field(s, diary, 'Mood', c, StatisticJournalType.FLOAT,
                            summary='[avg]',
                            display_cls=Score0)
            add_topic_field(s, diary, 'Nutrition', c, StatisticJournalType.TEXT,
                            summary='[cnt]',
                            display_cls=Text)
            add_topic_field(s, diary, 'Soreness', c, StatisticJournalType.TEXT,
                            summary='[cnt]',
                            display_cls=Text)
            add_topic_field(s, diary, 'Medication', c, StatisticJournalType.TEXT,
                            summary='[cnt]',
                            display_cls=Text)
            add_topic_field(s, diary, 'Weather', c, StatisticJournalType.TEXT,
                            summary='[cnt]',
                            display_cls=Text)
            add_topic_field(s, diary, 'Route', c, StatisticJournalType.TEXT,
                            summary='[cnt]',
                            display_cls=Text)

        # finally, set the TZ so that first use of the diary doesn't wipe all our intervals
        TopicJournal.check_tz(log, s)