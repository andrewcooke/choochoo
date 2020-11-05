
from logging import getLogger

from .climb import add_climb, CLIMB_CNAME
from .database import add_activity_group, Counter, add_process, add_displayer, add_constant, \
    add_diary_topic, add_diary_topic_field, add_activity_topic_field, add_activity_displayer_delegate, \
    add_activity_topic
from .impulse import add_responses, add_impulse
from ..diary.model import TYPE, EDIT, FLOAT, LO, HI, DP, SCORE
from ..lib.inspect import read_package
from ..lib.schedule import Schedule
from ..names import N, T, Sports, U, S
from ..pipeline.calculate import ImpulseCalculator
from ..pipeline.calculate.achievement import AchievementCalculator
from ..pipeline.calculate.activity import ActivityCalculator
from ..pipeline.calculate.climb import FindClimbCalculator
from ..pipeline.calculate.cluster import ClusterCalculator
from ..pipeline.calculate.elevation import ElevationCalculator
from ..pipeline.calculate.heart_rate import RestHRCalculator
from ..pipeline.calculate.kit import KitCalculator
from ..pipeline.calculate.nearby import SimilarityCalculator, NearbyCalculator
from ..pipeline.calculate.response import ResponseCalculator
from ..pipeline.calculate.sector import SectorCalculator
from ..pipeline.calculate.steps import StepsCalculator
from ..pipeline.calculate.summary import SummaryCalculator
from ..pipeline.display.activity.achievement import AchievementDelegate
from ..pipeline.display.activity.jupyter import JupyterDelegate
from ..pipeline.display.activity.nearby import NearbyDelegate
from ..pipeline.display.activity.utils import ActivityDisplayer, ActivityDelegate
from ..pipeline.display.database import DatabaseDisplayer
from ..pipeline.display.diary import DiaryDisplayer
from ..pipeline.display.monitor import MonitorDisplayer
from ..pipeline.display.response import ResponseDisplayer
from ..pipeline.read.activity import ActivityReader
from ..pipeline.read.garmin import GARMIN_USER, GARMIN_PASSWORD
from ..pipeline.read.monitor import MonitorReader
from ..sql import DiaryTopicJournal, StatisticJournalType, ActivityTopicField, ActivityTopic
from ..sql.types import short_cls
from ..srtm.file import SRTM1_DIR_CNAME

log = getLogger(__name__)

NOTES = 'Notes'

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
            self._load_sector_groups(s)
            self._load_read_pipeline(s)
            self._load_calculate_pipeline(s)
            self._load_diary_pipeline(s)
            self._load_constants(s)
            self._load_diary_topics(s, Counter())
            self._load_activity_topics(s, Counter())
            self._post(s)

    def _pre(self, s):
        pass

    def _post(self, s):
        self._load_sys(s)
        self._views(s)

    def _load_specific_activity_groups(self, s):
        # statistic rankings (best of month etc) are calculated per group
        self._load_activity_group(s, BIKE, 'Cycling activities')
        self._load_activity_group(s, RUN, 'Running activities')
        self._load_activity_group(s, SWIM, 'Swimming activities')
        self._load_activity_group(s, WALK, 'Walking activities')

    def _load_sector_groups(self, s):
        pass

    def _load_activity_group(self, s, title, description):
        log.debug(f'Loading activity group {title}')
        self._activity_groups[title] = \
            add_activity_group(s, title, len(self._activity_groups), description=description)

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
        return {'position_lat': (T.LATITUDE, U.DEG, StatisticJournalType.FLOAT),
                'position_long': (T.LONGITUDE, U.DEG, StatisticJournalType.FLOAT),
                'heart_rate': (T.HEART_RATE, U.BPM, StatisticJournalType.INTEGER),
                'enhanced_speed': (T.SPEED, U.MS, StatisticJournalType.FLOAT),
                'distance': (T.DISTANCE, U.KM, StatisticJournalType.FLOAT),
                'enhanced_altitude': (T.ALTITUDE, U.M, StatisticJournalType.FLOAT),
                'cadence': (T.CADENCE, U.RPM, StatisticJournalType.INTEGER)}

    def _load_read_pipeline(self, s):
        sport_to_activity = self._sport_to_activity()
        record_to_db = self._record_to_db()
        add_process(s, ActivityReader, owner_out=short_cls(ActivityReader),
                    sport_to_activity=sport_to_activity, record_to_db=record_to_db)
        add_process(s, MonitorReader)

    def _ff_parameters(self):
        return ((42, 1, 1, T.FITNESS_D % 42, 'fitness'),
                (7, 1, 5, T.FATIGUE_D % 7, 'fatigue'))

    def _load_power_statistics(self, s):
        # after elevation and before ff etc
        # defaults is none because configuration is complex
        pass

    def _load_ff_statistics(self, s, default_fthr=154):
        for activity_group in self._activity_groups.values():
            add_impulse(s, activity_group)
            # we need a value here for various UI reasons.  might as well use my own value...
            add_constant(s, T.FTHR, default_fthr,
                         description=f'''
Heart rate (in bpm) at functional threshold.

Your FTHR is the highest sustained heart rate you can maintain for long periods (an hour).
It is used to calculate how hard you are working (the Impulse) and, from that, 
your FF-model parameters (fitness and fatigue).
''',
                         activity_group=activity_group, units=U.BPM,
                         statistic_journal_type=StatisticJournalType.INTEGER)
        add_climb(s)  # default climb calculator
        add_responses(s, self._ff_parameters(), prefix=N.DEFAULT)

    def _load_standard_statistics(self, s, blockers=None):
        add_process(s, FindClimbCalculator, blocked_by=[ElevationCalculator],
                    owner_in=short_cls(ActivityReader), climb=CLIMB_CNAME)
        add_process(s, ClusterCalculator, blocked_by=[ElevationCalculator],
                    owner_in=short_cls(ActivityReader))
        blockers = self._sector_statistics(s, blockers=blockers)
        add_process(s, StepsCalculator, blocked_by=[MonitorReader],
                    owner_in=short_cls(MonitorReader))
        add_process(s, RestHRCalculator, blocked_by=[MonitorReader],
                    owner_in=short_cls(MonitorReader))
        add_process(s, KitCalculator, blocked_by=[ActivityReader],
                    owner_in=short_cls(ActivityReader))
        blockers = blockers or []
        add_process(s, ActivityCalculator,
                    blocked_by=blockers + [ElevationCalculator, ImpulseCalculator, ResponseCalculator,
                                           FindClimbCalculator],
                    owner_in=short_cls(ResponseCalculator),
                    response_prefix=N.DEFAULT)
        add_process(s, SimilarityCalculator, blocked_by=[ActivityCalculator],
                    owner_in=short_cls(ActivityCalculator))
        add_process(s, NearbyCalculator, blocked_by=[SimilarityCalculator],
                    owner_in=short_cls(SimilarityCalculator))

    def _sector_statistics(self, s, blockers=None):
        blockers = blockers or []
        add_process(s, SectorCalculator, blocked_by=[ClusterCalculator, FindClimbCalculator])
        blockers.append(SectorCalculator)
        return blockers

    def _load_summary_statistics(self, s):
        # need to call normalize here because schedule isn't a schedule type column,
        # but part of a kargs JSON blob.
        # also, add year first so that monthly doesn't get confused by extra stats range
        x = add_process(s, SummaryCalculator,
                        # relying on ActivityCalculator dependencies
                        blocked_by=[ActivityCalculator, RestHRCalculator, StepsCalculator],
                        schedule=Schedule.normalize('x'))
        y = add_process(s, SummaryCalculator, blocked_by=[x],
                        schedule=Schedule.normalize('y'))
        add_process(s, SummaryCalculator, blocked_by=[y],
                    schedule=Schedule.normalize('m'))

    def _load_calculate_pipeline(self, s):
        # order is important here because some pipelines expect values created by others
        # this converts RAW_ELEVATION to ELEVATION, if needed
        add_process(s, ElevationCalculator, blocked_by=[ActivityReader])
        blockers = self._load_power_statistics(s)
        self._load_ff_statistics(s)
        self._load_standard_statistics(s, blockers=blockers)
        self._load_summary_statistics(s)
        add_process(s, AchievementCalculator, blocked_by=[SummaryCalculator],
                    owner_in=short_cls(ActivityCalculator))

    def _load_diary_pipeline(self, s):
        add_displayer(s, DiaryDisplayer)
        add_displayer(s, MonitorDisplayer)
        # prefix ties in to the ff statistics config
        add_displayer(s, ResponseDisplayer, owner_in=short_cls(ResponseCalculator), prefix=N.DEFAULT)
        add_displayer(s, ActivityDisplayer)
        for delegate in self._activity_displayer_delegates():
            add_activity_displayer_delegate(s, delegate)
        add_displayer(s, DatabaseDisplayer)

    def _activity_displayer_delegates(self):
        return [AchievementDelegate, ActivityDelegate, NearbyDelegate, JupyterDelegate]

    def _load_constants(self, s):
        add_constant(s, SRTM1_DIR_CNAME, self._config.args._format(value='{data}/srtm1'),
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

    def _views(self, s):
        s.execute('''
create view statistics as
select n.name, n.owner,
       j.id as statistic_journal_id, j.time, j.source_id,
       coalesce(i.value::text, f.value::text, t.value, x.value::text) as value
  from statistic_name as n
  join statistic_journal as j on n.id = j.statistic_name_id
  left join statistic_journal_integer as i on i.id = j.id
  left join statistic_journal_float as f on f.id = j.id
  left join statistic_journal_text as t on t.id = j.id
  left join statistic_journal_timestamp as x on x.id = j.id;''')


def get_profiles():
    from . import profiles
    return dict(read_package(profiles))


def get_profile(name):
    return get_profiles()[name]
