
from .database import Counter, add_pipeline, add_activity, add_activity_constant, add_topic, add_topic_field
from ..lib.schedule import Schedule
from ..squeal.tables.statistic import StatisticType
from ..stoats.activity import ActivityStatistics
from ..stoats.clean import CleanUnusedStatistics
from ..stoats.names import BPM, FTHR
from ..stoats.summary import SummaryStatistics
from ..uweird.fields import Text, Float, Score, Integer


def default(db):

    with db.session_context() as s:

        # the following users heleper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        # statistics pipeline

        c = Counter()
        add_pipeline(s, ActivityStatistics, c)
        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        add_pipeline(s, SummaryStatistics, c, schedule=Schedule.normalize('m'))
        add_pipeline(s, SummaryStatistics, c, schedule=Schedule.normalize('y'))
        add_pipeline(s, CleanUnusedStatistics, c)

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
                        display_cls=Integer, display_kargs={'lo': 25, 'hi': 75})
        add_topic_field(s, diary, 'Weight', c,
                        units='kg', summary='[avg]',
                        display_cls=Float, display_kargs={'lo': 40, 'hi': 100, 'dp': 1})
        add_topic_field(s, diary, 'Sleep', c,
                        units='hr', summary='[avg]',
                        display_cls=Float, display_kargs={'lo': 0, 'hi': 24, 'dp': 1})
        add_topic_field(s, diary, 'Mood', c,
                        summary='[avg]',
                        display_cls=Score)
        add_topic_field(s, diary, 'Medication', c,
                        display_cls=Text)
