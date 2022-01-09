from ..climb import CLIMB_CNAME
from ..database import add_diary_topic, add_child_diary_topic, add_diary_topic_field, add_process, add_pipeline
from ..power import add_simple_power_estimate, add_kit_power_estimate, add_kit_power_model, POWER_MODEL_CNAME
from ..profile import WALK, SWIM, RUN, BIKE, Profile
from ...commands.args import DEFAULT
from ...common.names import TIME_ZERO
from ...diary.model import TYPE, EDIT
from ...lib import to_time, time_to_local_date
from ...names import Sports, simple_name, N
from ...pipeline.calculate import SectorCalculator, ElevationCalculator
from ...pipeline.calculate.climb import FindClimbCalculator
from ...pipeline.calculate.cluster import ClusterCalculator
from ...pipeline.calculate.power import PowerCalculator
from ...pipeline.calculate.sector import NewSectorCalculator
from ...pipeline.read.activity import ActivityReader
from ...sql import StatisticJournalType, StatisticName, DiaryTopic, DiaryTopicJournal, PipelineType
from ...sql.tables.sector import SectorGroup, DEFAULT_GROUP_RADIUS_KM
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ...sql.types import short_cls
from ...sql.utils import add


def acooke(config):
    '''
## acooke

This extends the garmin configuration with:

* Diary entries that I need
* Additional activity groups selected on the kit used
* Power estimates

Unlikely to be useful to others, but works as an example of how you can extend the code yourself.
    '''
    ACooke(config).load()


ROAD = 'Road'
MTB = 'MTB'


class ACooke(Profile):

    def _load_diary_topics(self, s, c):
        super()._load_diary_topics(s, c)

        # add more diary entries specific to my needs

        injuries = add_diary_topic(s, 'Injuries', c)

        ms = add_child_diary_topic(s, injuries, 'Multiple Sclerosis', c)
        add_diary_topic_field(s, ms, 'MS Notes', c, StatisticJournalType.TEXT, model={TYPE: EDIT})
        add_child_diary_topic(s, ms, 'Betaferon', c,
                              schedule='2018-08-08/2d[1]')  # reminder to take meds on alternate days

        leg = add_child_diary_topic(s, injuries, 'Broken Femur LHS', c,
                                    schedule='d2018-03-11-2020-03-01')
        add_diary_topic_field(s, leg, 'Leg Notes', c, StatisticJournalType.TEXT, model={TYPE: EDIT})
        add_child_diary_topic(s, leg, 'Learn to manage tendon pain', c)  # aims added as child topics
        add_child_diary_topic(s, leg, 'Maintain fitness', c)
        add_child_diary_topic(s, leg, 'Visit UK', c, schedule='-2018-08-11')

    def _load_specific_activity_groups(self, s):
        super()._load_specific_activity_groups(s)

        # additional activity groups for different cycling activities

        self._load_activity_group(s, ROAD, 'Road cycling activities')
        self._load_activity_group(s, MTB, 'MTB cycling activities')

    def _load_sector_groups(self, s):
        # note lon, lat for centre
        SectorGroup.add(s, (-70.7, -33.4), DEFAULT_GROUP_RADIUS_KM, 'Santiago, Chile')

    def _sport_to_activity(self):

        # map the additional groups above based on kit use

        return {Sports.SPORT_CYCLING: {
                    N.KIT: {
                        'cotic': simple_name(MTB),
                        'bowman': simple_name(ROAD),
                        'cbutler': simple_name(ROAD),
                    },
                    DEFAULT: simple_name(BIKE),
                },
                Sports.SPORT_RUNNING: simple_name(RUN),
                Sports.SPORT_SWIMMING: simple_name(SWIM),
                Sports.SPORT_WALKING: simple_name(WALK)}

    def _sector_statistics(self, s, power_statistics=None):
        power_statistics = power_statistics or []
        add_process(s, ClusterCalculator, blocked_by=[ElevationCalculator],
                    owner_in=short_cls(ActivityReader))
        climbs = ','.join(CLIMB_CNAME + str(index) for index in range(len(self._climb_phis)))
        for activity_group in (ROAD, MTB):
            add_process(s, FindClimbCalculator, blocked_by=[ElevationCalculator],
                        owner_in=short_cls(ActivityReader), climbs=climbs,
                        activity_group=activity_group)
            add_process(s, SectorCalculator, blocked_by=[ClusterCalculator, FindClimbCalculator],
                        power_model=POWER_MODEL_CNAME, activity_group=activity_group)
        return power_statistics + [SectorCalculator]

    def _load_sector_pipeline(self, s):
        for activity_group in (ROAD, MTB):
            add_pipeline(s, NewSectorCalculator, PipelineType.SECTOR, activity_group=activity_group)

    def _load_power_statistics(self, s, simple=False):
        # add power estimates for the two bikes
        # (note that this comes after standard stats, but before summary, achievements, etc).
        if simple:
            for activity_group in (MTB, ROAD):
                activity_group = self._activity_groups[activity_group]
                add_simple_power_estimate(s, activity_group, 0.42, 0.0055, 12, 65)
        else:
            add_kit_power_estimate(s, (MTB, ROAD))
            for kit, activity_group, cda, crr, bike_weight in (('cotic', MTB, 0.42, 0.0055, 12),
                                                               ('bowman', ROAD, 0.42, 0.0055, 8),
                                                               ('cbutler', ROAD, 0.42, 0.0055, 12)):
                add_kit_power_model(s, kit, self._activity_groups[activity_group], cda, crr, bike_weight)
        return [PowerCalculator]  # additional blocker for activity stats

    def _post(self, s):
        # set a default weight for early power calculations
        weight = s.query(StatisticName).filter(StatisticName.name == 'Weight', StatisticName.owner == DiaryTopic).one()
        diary = add(s, DiaryTopicJournal(date=time_to_local_date(to_time(0.0))))
        add(s, STATISTIC_JOURNAL_CLASSES[weight.statistic_journal_type](
            value=65.0, time=TIME_ZERO, statistic_name=weight, source=diary))
        super()._post(s)
