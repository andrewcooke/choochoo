
from .database import Counter, add_statistics, add_activity_group, add_activity_constant, add_topic, add_topic_field, \
    add_diary, add_activities, add_monitor, name_constant
from .impulse import add_impulse, FITNESS_CNAME, FATIGUE_CNAME
from ..lib.schedule import Schedule
from ..squeal.tables.statistic import StatisticJournalType
from ..squeal.tables.topic import TopicJournal
from ..stoats.calculate.activity import ActivityStatistics
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.calculate.segment import SegmentStatistics
from ..stoats.calculate.summary import SummaryStatistics
from ..stoats.display.activity import ActivityDiary
from ..stoats.display.impulse import ImpulseDiary
from ..stoats.display.monitor import MonitorDiary
from ..stoats.names import BPM, FTHR
from ..stoats.read.activity import ActivityImporter
from ..stoats.read.monitor import MonitorImporter
from ..uweird.fields.topic import Text, Float, Score0


def default(log, db, no_diary=False):

    with db.session_context() as s:

        # the following users helper functions (add_...) but you can also
        # execute arbitrary python code, use the session, etc.

        # basic activities

        c = Counter()
        bike = add_activity_group(s, 'Bike', c, description='All cycling activities')
        run = add_activity_group(s, 'Run', c, description='All running activities')
        # sport_to_activity maps from the FIT sport field to the activity defined above
        add_activities(s, ActivityImporter, c, sport_to_activity={'cycling': bike.name,
                                                                  'running': run.name})

        # statistics pipeline (called to calculate missing statistics)

        c = Counter()
        add_statistics(s, ActivityStatistics, c)
        add_statistics(s, SegmentStatistics, c)
        add_statistics(s, MonitorStatistics, c)
        add_impulse(s, c, bike)  # parameters set here can be adjusted via constants command

        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('m'))
        add_statistics(s, SummaryStatistics, c, schedule=Schedule.normalize('y'))

        # diary pipeline (called to display data in the diary)

        c = Counter()
        add_diary(s, MonitorDiary, c)
        # these tie-in to the constants used in add_impulse()
        add_diary(s, ImpulseDiary, c,
                  fitness=name_constant(FITNESS_CNAME, bike),
                  fatigue=name_constant(FATIGUE_CNAME, bike))
        add_diary(s, ActivityDiary, c)

        # monitor pipeline

        c = Counter()
        add_monitor(s, MonitorImporter, c)

        # constants used by statistics

        add_activity_constant(s, bike, FTHR,
                              description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
        add_activity_constant(s, run, FTHR,
                              description='Heart rate at functional threshold (running).',
                              units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)

        if not no_diary:

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

        # finally, set the TZ so that first use of teh diary doesn't wipe all our intervals
        TopicJournal.check_tz(log, s)