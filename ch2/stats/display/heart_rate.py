
from urwid import Text, Pile

from ..calculate.activity import ActivityCalculator
from ..names import PERCENT_IN_Z_ANY
from ...diary.model import value
from ...sql.tables.statistic import StatisticJournal, StatisticName


def build_zones(s, ajournal, width):
    body = []
    percent_times = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticJournal.time == ajournal.start,
               StatisticName.name.like(PERCENT_IN_Z_ANY),
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group) \
        .order_by(StatisticName.name).all()
    for zone, percent_time in reversed(list(enumerate(percent_times, start=1))):
        text = ('%d:' + ' ' * (width - 6) + '%3d%%') % (zone, int(0.5 + percent_time.value))
        column = 100 / width
        left = int((percent_time.value + 0.5 * column) // column)
        text_left = text[0:left]
        text_right = text[left:]
        body.append(Text([('zone-%d' % zone, text_left), text_right]))
    return Pile(body)


# todo - why is this here and not in activity?  is the above used in a template?
def read_zones(s, ajournal):
    percent_times = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticJournal.time == ajournal.start,
               StatisticName.name.like(PERCENT_IN_Z_ANY),
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group) \
        .order_by(StatisticName.name).all()
    if percent_times:
        for zone, percent_time in reversed(list(enumerate((time.value for time in percent_times), start=1))):
            yield [value('Zone', zone, tag='hr-zone'), value('Percent time', percent_time)]
