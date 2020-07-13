
from logging import getLogger

from .climb import add_climb, CLIMB_CNAME
from .database import add_activity_group, add_activities, Counter, add_statistics, add_displayer, \
    add_monitor, add_constant, add_diary_topic, add_diary_topic_field, \
    add_activity_topic_field, add_activity_displayer_delegate, add_activity_topic
from .impulse import add_responses, add_impulse
from ..commands.garmin import GARMIN_USER, GARMIN_PASSWORD
from ..diary.model import TYPE, EDIT, FLOAT, LO, HI, DP, SCORE
from ..lib.schedule import Schedule
from ..names import N, Titles, Sports, Units, Summaries as S
from ..pipeline.calculate import ImpulseCalculator
from ..pipeline.calculate.achievement import AchievementCalculator
from ..pipeline.calculate.activity import ActivityCalculator
from ..pipeline.calculate.elevation import ElevationCalculator
from ..pipeline.calculate.heart_rate import RestHRCalculator
from ..pipeline.calculate.kit import KitCalculator
from ..pipeline.calculate.monitor import MonitorCalculator
from ..pipeline.calculate.nearby import SimilarityCalculator, NearbyCalculator
from ..pipeline.calculate.power import PowerCalculator
from ..pipeline.calculate.response import ResponseCalculator
from ..pipeline.calculate.segment import SegmentCalculator
from ..pipeline.calculate.summary import SummaryCalculator
from ..pipeline.display.activity.achievement import AchievementDelegate
from ..pipeline.display.activity.jupyter import JupyterDelegate
from ..pipeline.display.activity.nearby import NearbyDelegate
from ..pipeline.display.activity.segment import SegmentDelegate
from ..pipeline.display.activity.utils import ActivityDisplayer, ActivityDelegate
from ..pipeline.display.database import DatabaseDisplayer
from ..pipeline.display.diary import DiaryDisplayer
from ..pipeline.display.monitor import MonitorDisplayer
from ..pipeline.display.response import ResponseDisplayer
from ..pipeline.read.monitor import MonitorReader
from ..pipeline.read.segment import SegmentReader
from ..sql import DiaryTopicJournal, StatisticJournalType, ActivityTopicField, ActivityTopic
from ..sql.types import short_cls
from ..srtm.file import SRTM1_DIR_CNAME

log = getLogger(__name__)

NOTES = 'Notes'

BROKEN = 'broken'

BIKE = 'Bike'
RUN = 'Run'
SWIM = 'Swim'
WALK = 'Walk'


class Profile:
    '''
    A class-based approach so that we can easily modify the config for different profiles.
    '''

    def __init__(self, config):
        self._config = config
        self._activity_groups = {}

    def load(self):
        with self._config.db.session_context() as s:
            # hopefully you won't need to over-ride this, but instead one of the more specific methods
            self._pre(s)
            self._load_specific_activity_groups(s)
            self._load_activities_pipeline(s, Counter())
            self._load_statistics_pipeline(s, Counter())
            self._load_diary_pipeline(s, Counter())
            self._load_monitor_pipeline(s, Counter())
            self._load_constants(s)
            self._load_diary_topics(s, Counter())
            self._load_activity_topics(s, Counter())
            self._post_diary(s)
            self._post(s)

    def _pre(self, s):
        pass

    def _post_diary(self, s):
        pass

    def _post(self, s):
        self._load_sys(s)

    def _load_specific_activity_groups(self, s):
        # statistic rankings (best of month etc) are calculated per group
        self._load_activity_group(s, BIKE, 'Cycling activities')
        self._load_activity_group(s, RUN, 'Running activities')
        self._load_activity_group(s, SWIM, 'Swimming activities')
        self._load_activity_group(s, WALK, 'Walking activities')

    def _load_activity_group(self, s, name, description):
        log.debug(f'Loading activity group {name}')
        self._activity_groups[name] = \
            add_activity_group(s, name, len(self._activity_groups), description=description)

    def _sport_to_activity(self):
        # sport_to_activity maps from the FIT sport field to the activity defined above.
        # more complex mapping is supported using kits (see acooke configuration),
        return {Sports.SPORT_CYCLING: BIKE,
                Sports.SPORT_RUNNING: RUN,
                Sports.SPORT_SWIMMING: SWIM,
                Sports.SPORT_WALKING: WALK}

    def _record_to_db(self):
        # the mapping from FIT fields to database entries
        # you really don't want to alter this unless you know what you are doing...
        # todo - should this depend on activity group?
        return {'position_lat': (Titles.LATITUDE, Units.DEG, StatisticJournalType.FLOAT),
                'position_long': (Titles.LONGITUDE, Units.DEG, StatisticJournalType.FLOAT),
                'heart_rate': (Titles.HEART_RATE, Units.BPM, StatisticJournalType.INTEGER),
                'enhanced_speed': (Titles.SPEED, Units.MS, StatisticJournalType.FLOAT),
                'distance': (Titles.DISTANCE, Units.KM, StatisticJournalType.FLOAT),
                'enhanced_altitude': (Titles.ALTITUDE, Units.M, StatisticJournalType.FLOAT),
                'cadence': (Titles.CADENCE, Units.RPM, StatisticJournalType.INTEGER)}

    def _load_activities_pipeline(self, s, c):
        sport_to_activity = self._sport_to_activity()
        record_to_db = self._record_to_db()
        add_activities(s, SegmentReader, c, owner_out=short_cls(SegmentReader),
                       sport_to_activity=sport_to_activity, record_to_db=record_to_db)

    def _ff_parameters(self):
        return ((42, 1, 1, Titles.FITNESS_D % 42, 'fitness'),
                (7, 1, 5, Titles.FATIGUE_D % 7, 'fatigue'))

    def _load_power_statistics(self, s, c):
        # after elevation and before ff etc
        # defaults is none because configuration is complex
        pass

    def _load_ff_statistics(self, s, c, default_fthr=154):
        for activity_group in self._activity_groups.values():
            add_impulse(s, c, activity_group)
            # we need a value here for various UI reasons.  might as well use my own value...
            add_constant(s, Titles.FTHR, default_fthr,
                         description=f'''
Heart rate (in bpm) at functional threshold.

Your FTHR is the highest sustained heart rate you can maintain for long periods (an hour).
It is used to calculate how hard you are working (the Impulse) and, from that, 
your FF-model parameters (fitness and fatigue).
''',
                         activity_group=activity_group, units=Units.BPM,
                         statistic_journal_type=StatisticJournalType.INTEGER)
        add_climb(s)  # default climb calculator
        add_responses(s, c, self._ff_parameters(), prefix=N.DEFAULT)

    def _load_standard_statistics(self, s, c):
        add_statistics(s, SegmentCalculator, c, owner_in=short_cls(SegmentReader))
        add_statistics(s, MonitorCalculator, c, owner_in=short_cls(MonitorReader))
        add_statistics(s, RestHRCalculator, c, owner_in=short_cls(MonitorReader))
        add_statistics(s, KitCalculator, c, owner_in=short_cls(SegmentReader))
        add_statistics(s, ActivityCalculator, c,
                       blocked_by=[PowerCalculator, ElevationCalculator, ImpulseCalculator, ResponseCalculator],
                       owner_in=short_cls(ResponseCalculator),
                       climb=CLIMB_CNAME, response_prefix=N.DEFAULT)
        add_statistics(s, SimilarityCalculator, c,
                       blocked_by=[ActivityCalculator],
                       owner_in=short_cls(ActivityCalculator))
        add_statistics(s, NearbyCalculator, c,
                       blocked_by=[SimilarityCalculator],
                       owner_in=short_cls(SimilarityCalculator))

    def _load_summary_statistics(self, s, c):
        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        # also, add year first so that monthly doesn't get confused by extra stats range
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('x'))
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('y'))
        add_statistics(s, SummaryCalculator, c, schedule=Schedule.normalize('m'))

    def _load_statistics_pipeline(self, s, c):
        # order is important here because some pipelines expect values created by others
        # this converts RAW_ELEVATION to ELEVATION, if needed
        add_statistics(s, ElevationCalculator, c)
        self._load_power_statistics(s, c)
        self._load_ff_statistics(s, c)
        self._load_standard_statistics(s, c)
        self._load_summary_statistics(s, c)
        add_statistics(s, AchievementCalculator, c, owner_in=short_cls(ActivityCalculator))

    def _load_diary_pipeline(self, s, c):
        add_displayer(s, DiaryDisplayer, c)
        add_displayer(s, MonitorDisplayer, c)
        # prefix ties in to the ff statistics config
        add_displayer(s, ResponseDisplayer, c, owner_in=short_cls(ResponseCalculator), prefix=N.DEFAULT)
        add_displayer(s, ActivityDisplayer, c)
        c2 = Counter()
        for delegate in self._activity_displayer_delegates():
            add_activity_displayer_delegate(s, delegate, c2)
        add_displayer(s, DatabaseDisplayer, c)

    def _activity_displayer_delegates(self):
        return [AchievementDelegate, ActivityDelegate, SegmentDelegate, NearbyDelegate, JupyterDelegate]

    def _load_monitor_pipeline(self, s, c):
        add_monitor(s, MonitorReader, c)

    def _load_constants(self, s):
        add_constant(s, SRTM1_DIR_CNAME, self._config.args._format(value='{data-dir}/srtm1'),
                     description='''
Directory containing SRTM1 hgt files for elevations.

These data are used to give improved values when using GPS elevation.
You must create the directory and populate it with suitable files from http://dwtkns.com/srtm30m.
If the directory or files are missing the raw GPS elevation will be used.
This is noted as a warning in the logs (along with the name of the missing file).
''',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)
        add_constant(s, GARMIN_USER, None,
                     description='''
User for Garmin.
If set, monitor data (daily steps, heart rate) are downloaded from Garmin.
''',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)
        add_constant(s, GARMIN_PASSWORD, None,
                     description='''
Password for Garmin.
This is stored as plaintext on the server (and visible here)
so do not use an important password that applies to many accounts.
''',
                     single=True, statistic_journal_type=StatisticJournalType.TEXT)

    def _load_diary_topics(self, s, c):
        # the fields you see every day in the diary
        diary = add_diary_topic(s, 'Status', c)
        add_diary_topic_field(s, diary, 'Notes', c, StatisticJournalType.TEXT,
                              model={TYPE: EDIT}, description='Daily notes recorded by user in diary.')
        add_diary_topic_field(s, diary, 'Weight', c, StatisticJournalType.FLOAT,
                              units='kg', summary=S.join(S.AVG, S.MSR),
                              description='Weight recorded by user in diary.',
                              model={TYPE: FLOAT, LO: 50, HI: 100, DP: 1})
        add_diary_topic_field(s, diary, 'Sleep', c, StatisticJournalType.FLOAT,
                              units='h', summary=S.AVG, description='Sleep time recorded by user in diary.',
                              model={TYPE: FLOAT, LO: 0, HI: 24, DP: 1})
        add_diary_topic_field(s, diary, 'Mood', c, StatisticJournalType.FLOAT,
                              summary=S.AVG, description='Mood recorded by user in diary.',
                              model={TYPE: SCORE})
        add_diary_topic_field(s, diary, 'Medication', c, StatisticJournalType.TEXT,
                              summary=S.CNT, description='Medication recorded by user in diary.',
                              model={TYPE: EDIT})
        add_diary_topic_field(s, diary, 'Weather', c, StatisticJournalType.TEXT,
                              summary=S.CNT, description='Weather recorded by user in diary.',
                              model={TYPE: EDIT})

    def _load_activity_topics(self, s, c):
        # the fields in the diary that are displayed for each activity
        for activity_group in self._activity_groups.values():
            c = Counter()
            root = add_activity_topic(s, ActivityTopic.ROOT, c, description=ActivityTopic.ROOT_DESCRIPTION,
                                      activity_group=activity_group)
            add_activity_topic_field(s, root, 'Name', c, StatisticJournalType.TEXT,
                                     activity_group, model={TYPE: EDIT},
                                     description=ActivityTopicField.NAME_DESCRIPTION)
            # note that these have empty toic parents because they are children of the entry itself
            if activity_group.name != SWIM:
                add_activity_topic_field(s, root, 'Route', c, StatisticJournalType.TEXT,
                                         activity_group, model={TYPE: EDIT},
                                         description='Route recorded by user in diary.')
            add_activity_topic_field(s, root, NOTES, c, StatisticJournalType.TEXT,
                                     activity_group, model={TYPE: EDIT},
                                     description='Activity notes recorded by user in diary.')

    def _load_sys(self, s):
        # finally, update the timezone
        DiaryTopicJournal.check_tz(self._config, s)

