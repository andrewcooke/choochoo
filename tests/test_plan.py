
from choochoo.args import parser, NamespaceWithVariables
from choochoo.log import make_log
from choochoo.plan.weekly import Week, Day
from choochoo.squeal.database import Database
from choochoo.squeal.schedule import Schedule


def test_plan():

    plan = Week(title='British Cycling 12 Week improver',
                description='https://www.britishcycling.org.uk/zuvvi/media/bc_files/sportivetrainingplans/improver_plan/TRAINING_PLAN_-_Improvers_plan.pdf',
                start='2018-07-22',
                days={
                    'mon': Day(title='Rest day'),
                    'tue': Day(title='Outdoor / indoor',
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
                    'wed': Day(title='Rest day'),
                    'thu': Day(title='Outdoor / indoor',
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
                    'fri': Day(title='Cross-training',
                               notes=[(3,
                                       ((3, 'Bonus session - non-cycling activity'),
                                        'Rest day'))
                                      ]),
                    'sat': Day(title='Flexible day',
                               notes=[(11, None),
                                      '30m / low / improvers pre-event ride'
                                      ]),
                    'sun': Day(title='Outdoor ride',
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

    p = parser()
    args = NamespaceWithVariables(p.parse_args(['--database', ':memory:', 'diary']))
    log = make_log(args)
    db = Database(args, log)
    with db.session_context() as session:
        plan.create(log, session)
        session.flush()

    root = session.query(Schedule).filter(Schedule.parent_id == None).one()
    assert len(root.children) == 7, root.children
    for child in root.children:
        print(child)