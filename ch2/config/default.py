
from .database import Counter, add_statistics, add_activity, add_activity_constant, add_topic, add_topic_field, \
    add_diary
from ..lib.schedule import Schedule
from ..squeal.tables.statistic import StatisticType
from ..stoats.calculate.activity import ActivityStatistics
from ..stoats.display.activity import ActivityDiary
from ..stoats.calculate.clean import CleanUnusedStatistics
from ..stoats.names import BPM, FTHR
from ..stoats.calculate.summary import SummaryStatistics
from ..uweird.fields import Text, Float, Score, Integer


def default(db):

    with db.session_context() as s:

        # the following users heleper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        # statistics pipeline (called to calculate missing statistics)

        c = Counter()
        add_statistics(s, ActivityStatistics, c)
        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('m'))
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('y'))
        add_statistics(s, CleanUnusedStatistics, c)

        # diary pipeline (called to display data in the diary)

        c = Counter()
        add_diary(s, ActivityDiary, c)

        # basic activities

        bike = add_activity(s, 'Bike', c, description='All cycling activities')
        run = add_activity(s, 'Run', c, description='All running activities')
        s.flush()  # set IDs because these are used below

        # constants used by statistics

        add_activity_constant(s, bike, FTHR,
                              description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                              units=BPM, type=StatisticType.INTEGER)
        add_activity_constant(s, run, FTHR,
                              description='Heart rate at functional threshold (running).',
                              units=BPM, type=StatisticType.INTEGER)

        # a basic diary

        c = Counter()
        diary = add_topic(s, 'Diary', c)
        add_topic_field(s, diary, 'Notes', c,
                        display_cls=Text)
        add_topic_field(s, diary, 'Rest HR', c,
                        units=BPM, summary='[avg]',
                        display_cls=Integer, lo=25, hi=75)
        add_topic_field(s, diary, 'Weight', c,
                        units='kg', summary='[avg]',
                        display_cls=Float, lo=50, hi=100, dp=1)
        add_topic_field(s, diary, 'Sleep', c,
                        units='hr', summary='[avg]',
                        display_cls=Float, lo=0, hi=24, dp=1)
        add_topic_field(s, diary, 'Mood', c,
                        summary='[avg]',
                        display_cls=Score)
        add_topic_field(s, diary, 'Weather', c,
                        display_cls=Text)
        add_topic_field(s, diary, 'Medication', c,
                        display_cls=Text)
