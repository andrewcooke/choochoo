
import datetime as dt

from .database import Counter, add_statistics, add_activity_group, add_activity_constant, add_topic, add_topic_field, \
    add_diary, add_activities, add_monitor
from ..lib.schedule import Schedule
from ..squeal.tables.statistic import StatisticJournalType
from ..squeal.types import short_cls
from ..stoats.calculate.activity import ActivityStatistics
from ..stoats.calculate.heart_rate import HeartRateStatistics
from ..stoats.calculate.impulse import ImpulseStatistics, Response, Impulse
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.calculate.summary import SummaryStatistics
from ..stoats.display.activity import ActivityDiary
from ..stoats.display.monitor import MonitorDiary
from ..stoats.names import BPM, FTHR, HR_IMPULSE
from ..stoats.read.activity import ActivityImporter
from ..stoats.read.monitor import MonitorImporter
from ..uweird.fields.topic import Text, Float, Score0


def default(db):

    with db.session_context() as s:

        # the following users heleper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        # basic activities

        bike = add_activity_group(s, 'Bike', c, description='All cycling activities')
        run = add_activity_group(s, 'Run', c, description='All running activities')
        # sport_to_activity maps from the FIT sport field to the activity defined above
        add_activities(s, ActivityImporter, c, sport_to_activity={'cycling': bike.name,
                                                                  'running': run.name})
        s.flush()  # set IDs because these are used below

        # statistics pipeline (called to calculate missing statistics)

        c = Counter()
        add_statistics(s, ActivityStatistics, c)
        add_statistics(s, HeartRateStatistics, c)
        add_statistics(s, MonitorStatistics, c)
        add_statistics(s, ImpulseStatistics, 99,
                       responses=(
                           Response(name='Fitness', tau=dt.timedelta(days=20).total_seconds(),
                                    scale=1, start=0)._asdict(),
                           Response(name='Fatigue', tau=dt.timedelta(days=10).total_seconds(),
                                    scale=1, start=0)._asdict()),
                       impulse=Impulse(name=HR_IMPULSE, owner=short_cls(HeartRateStatistics),
                                       constraint=str(bike))._asdict()
                       )
        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('m'))
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('y'))

        # diary pipeline (called to display data in the diary)

        c = Counter()
        add_diary(s, MonitorDiary, c)
        add_diary(s, ActivityDiary, c)

        # monitor pipeline

        add_monitor(s, MonitorImporter, c)

        # constants used by statistics

        add_activity_constant(s, bike, FTHR,
                              description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, run, FTHR,
                              description='Heart rate at functional threshold (running).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)

        # a basic diary

        c = Counter()
        diary = add_topic(s, 'Diary', c)
        add_topic_field(s, diary, 'Notes', c,
                        display_cls=Text)
        # now provided via monitor
        # add_topic_field(s, diary, 'Rest HR', c,
        #                 units=BPM, summary='[avg]',
        #                 display_cls=Integer, lo=25, hi=75)
        add_topic_field(s, diary, 'Weight', c,
                        units='kg', summary='[avg]',
                        display_cls=Float, lo=50, hi=100, dp=1)
        add_topic_field(s, diary, 'Sleep', c,
                        units='h', summary='[avg]',
                        display_cls=Float, lo=0, hi=24, dp=1)
        add_topic_field(s, diary, 'Mood', c,
                        summary='[avg]',
                        display_cls=Score0)
        add_topic_field(s, diary, 'Nutrition', c,
                        summary='[cnt]',
                        display_cls=Text)
        add_topic_field(s, diary, 'Soreness', c,
                        summary='[cnt]',
                        display_cls=Text)
        add_topic_field(s, diary, 'Medication', c,
                        summary='[cnt]',
                        display_cls=Text)
        add_topic_field(s, diary, 'Weather', c,
                        summary='[cnt]',
                        display_cls=Text)
        add_topic_field(s, diary, 'Route', c,
                        summary='[cnt]',
                        display_cls=Text)
