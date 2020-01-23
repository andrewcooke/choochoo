
from .default import default
from ..config.database import Counter, add_diary_topic, add_child_diary_topic, add_diary_topic_field
from ..diary.model import TYPE, TEXT
from ..sql import StatisticJournalType
from ..urwid.fields.topic import Text


def acooke(system, db):

    default(system, db)

    with db.session_context() as s:

        c = Counter(100)

        injuries = add_diary_topic(s, 'Injuries', c)

        ms = add_child_diary_topic(s, injuries, 'Multiple Sclerosis', c)
        add_diary_topic_field(s, ms, 'Notes', c, StatisticJournalType.TEXT, model={TYPE: TEXT})
        add_child_diary_topic(s, ms, 'Betaferon', c,
                              schedule='2018-08-07/2d[1]')  # reminder to take meds on alternate days

        leg = add_child_diary_topic(s, injuries, 'Broken Femur LHS', c,
                                    schedule='2018-03-11-')
        add_diary_topic_field(s, leg, 'Notes', c, StatisticJournalType.TEXT, model={TYPE: TEXT})
        add_child_diary_topic(s, leg, 'Learn to manage tendon pain', c)  # aims added as child topics
        add_child_diary_topic(s, leg, 'Maintain fitness', c)
        add_child_diary_topic(s, leg, 'Visit UK', c,
                              schedule='-2018-08-11')
