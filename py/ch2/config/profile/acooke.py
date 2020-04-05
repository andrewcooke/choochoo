
from ..config import Config, WALK, SWIM, RUN
from ..database import add_diary_topic, add_child_diary_topic, add_diary_topic_field, add_nearby
from ..power import add_power_estimate
from ...diary.model import TYPE, TEXT
from ...sql import StatisticJournalType
from ...stats.names import SPORT_CYCLING, SPORT_RUNNING, SPORT_SWIMMING, SPORT_WALKING


def acooke(sys, s, no_diary):
    '''
## acooke

This extends the default configuration with:

* Diary entries that I need
* Additional activity groups selected on the kit used
* Power estimates
* An area around Santiago, Chile, for registering nearby activities

Unlikely to be useful to others, but works as an example of how you can extend the code yourself.
    '''
    ACooke(sys, no_diary=no_diary).load(s)


ROAD = 'Road'
MTB = 'MTB'


class ACooke(Config):

    def _load_diary_topics(self, s, c):
        super()._load_diary_topics(s, c)

        # add more diary entries specific to my needs

        injuries = add_diary_topic(s, 'Injuries', c)

        ms = add_child_diary_topic(s, injuries, 'Multiple Sclerosis', c)
        add_diary_topic_field(s, ms, 'Notes', c, StatisticJournalType.TEXT, model={TYPE: TEXT})
        add_child_diary_topic(s, ms, 'Betaferon', c,
                              schedule='2018-08-07/2d[1]')  # reminder to take meds on alternate days

        leg = add_child_diary_topic(s, injuries, 'Broken Femur LHS', c,
                                    schedule='2018-03-11-2020-04-01')
        add_diary_topic_field(s, leg, 'Notes', c, StatisticJournalType.TEXT, model={TYPE: TEXT})
        add_child_diary_topic(s, leg, 'Learn to manage tendon pain', c)  # aims added as child topics
        add_child_diary_topic(s, leg, 'Maintain fitness', c)
        add_child_diary_topic(s, leg, 'Visit UK', c, schedule='-2018-08-11')

    def _load_specific_activity_groups(self, s):
        super()._load_specific_activity_groups(s)

        # additional activity groups for different cycling activities

        self._load_activity_group(s, ROAD, 'Road cycling activities')
        self._load_activity_group(s, MTB, 'MTB cycling activities')

    def _sport_to_activity(self):

        # map the additional groups above based on kit use
        # (cotic and bowman are kit items added via kit commands)

        return {SPORT_CYCLING: {
                    'kit': {
                        'cotic': MTB,
                        'bowman': ROAD
                    }
                },
                SPORT_RUNNING: RUN,
                SPORT_SWIMMING: SWIM,
                SPORT_WALKING: WALK}

    def _load_standard_statistics(self, s, c):
        super()._load_standard_statistics(s, c)

        # add power estimates for the two bikes
        # (note that this comes after standard stats, but before summary, achievements, etc).

        for name in (MTB, ROAD):
            add_power_estimate(s, c, self._activity_groups[name], vary='')

    def _load_statistics_pipeline(self, s, c):
        super()._load_statistics_pipeline(s, c)

        # define spatial regions for nearby routes etc

        for name in (MTB, ROAD, WALK):
            add_nearby(s, c, self._activity_groups[name], 'Santiago', -33.4, -70.4, fraction=0.1, border=150)

