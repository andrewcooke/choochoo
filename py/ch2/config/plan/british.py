
from .weekly import Week, Day


def twelve_week_improver(date):
    """
    The twelve-week plan described at https://www.britishcycling.org.uk.
    Takes a single argument: the start date.
    """

    return Week(name='British Cycling 12 Week improver',
                description='https://www.britishcycling.org.uk/zuvvi/media/bc_files/sportivetrainingplans/improver_plan/TRAINING_PLAN_-_Improvers_plan.pdf',
                start=date,
                days={
                    'mon': Day(name='Rest day'),
                    'tue': Day(name='Outdoor / indoor',
                               notes=['1h / low / easy ride',
                                      '1h / med / zone build',
                                      '1h / med / zone build',
                                      '1h / low / spin out session',
                                      '1h / med / sweet spot intervals',
                                      '1h / med / sweet spot intervals',
                                      '1h20m / med/high / 3x10m',
                                      '40m / low/med / extended warm-up',
                                      '40m / med/high / threshold test',
                                      '1h20m / med / 2x20m sweet spot',
                                      '1h / high / VO2 intervals',
                                      '1h / low / spin out session'
                                      ]
                               ),
                    'wed': Day(name='Rest day'),
                    'thu': Day(name='Outdoor / indoor',
                               notes=['1h10m / med/high / threshold test',
                                      '1h / med / tempo intervals',
                                      '1h / med / tempo intervals',
                                      '20m / low/med / warm-up',
                                      '1h / med/high / pyramid intervals 1',
                                      '1h / med/high / pyramid intervals 1',
                                      '1h20m / med/high / 2x10m',
                                      '1h / low / spin out session',
                                      '1h2om / med / 2x20m',
                                      '1h / high / VO2 intervals',
                                      '45m / low / improvers recovery ride',
                                      '1h / low / spin out session'
                                      ]
                               ),
                    'fri': Day(name='Cross-training',
                               notes=3 * (3 * ['Bonus session - non-cycling activity'] + ['Rest day'])),
                    'sat': Day(name='Flexible day',
                               notes=11 * [None] + ['30m / low / improvers pre-event ride']),
                    'sun': Day(name='Outdoor ride',
                               notes=['1h30m / low/med / improvers endurance ride',
                                      '1h40m / low/med / improvers endurance ride',
                                      '1h50m / low/med / improvers endurance ride',
                                      '2h30m / low/med / improvers endurance ride',
                                      '2h / low/med / improvers endurance ride',
                                      '2h15m / low/med / improvers endurance ride',
                                      '2h130 / low/med / improvers endurance ride',
                                      '2h/60km / low/med / improvers endurance ride',
                                      '3h/75km / low/med/high / endurance ride with long tempo rides and sprints',
                                      '3h45m/75km / low/med / improvers endurance ride',
                                      '2h / low/med / improvers recovery ride',
                                      '5h/100kn / low/med / improvers endurance ride'
                                      ])
                })
