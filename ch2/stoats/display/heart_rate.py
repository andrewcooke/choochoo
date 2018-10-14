
from urwid import Text, Pile

from ..names import PERCENT_IN_Z_ANY
from ...squeal.tables.statistic import StatisticJournal, Statistic


def build_zones(s, journal, width):
    body = []
    percent_times = s.query(StatisticJournal).join(Statistic). \
        filter(StatisticJournal.source == journal,
               Statistic.name.like(PERCENT_IN_Z_ANY)) \
        .order_by(Statistic.name).all()
    for zone, percent_time in reversed(list(enumerate(percent_times, start=1))):
        text = ('%d:' + ' ' * (width - 6) + '%3d%%') % (zone, int(0.5 + percent_time.value))
        column = 100 / width
        left = int((percent_time.value + 0.5 * column) // column)
        text_left = text[0:left]
        text_right = text[left:]
        body.append(Text([('zone-%d' % zone, text_left), text_right]))
    return Pile(body)
