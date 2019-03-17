
import datetime as dt
from calendar import monthrange
from logging import getLogger

from colorama import init, Fore, Style

from ch2.lib.schedule import Schedule
from ..lib.date import to_date, add_date, MONTH
from ..commands.args import SCHEDULE, MONTHS, START

log = getLogger(__name__)
INDENT = '   '


def test_schedule(args, db):
    '''
## test-schedule

    > ch2 test-schedule SCHEDULE

Print a calendar showing how the given schedule is interpreted.

### Example

    > ch2 test-schedule 2w[1mon,2sun]

(Try it and see)
    '''
    schedule, start, months = Schedule(args[SCHEDULE]), to_date(args[START], none=True), args[MONTHS]
    if not start:
        start = dt.date.today()
    start = dt.date(start.year, start.month, 1)
    if not months:
        months = 3
    print_calendar(schedule, start, months)


def print_calendar(schedule, start, months):
    init()
    frame, next_frame = 0, schedule.next_frame(start)
    for _ in range(months):
        print()
        print(INDENT, end='')
        title = start.strftime('%B %Y')
        print(' ' * (11 - len(title) // 2) + title)
        print(INDENT, end='')
        for day in ('Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'):
            print(' %s' % day, end='')
        print()
        for week in month_days(start):
            print(INDENT, end='')
            for day in week:
                if not day:
                    print('   ', end='')
                else:
                    date = dt.date(start.year, start.month, day)
                    if date >= next_frame:
                        frame += 1
                        next_frame = schedule.next_frame(date)
                    if schedule.at_location(date):
                        colour = Fore.RED if frame % 2 else Fore.GREEN
                        print(colour + ' %2d' % day + Style.RESET_ALL, end='')
                    else:
                        print(' %2d' % day, end='')
            print()
        start = add_date(start, (1, MONTH))
    print()


def month_days(date):
    dow, n = monthrange(date.year, date.month)
    start = -dow
    while start < n:
        week = []
        if start < 0:
            week += [None] * -start
        week += list(range(max(0, start) + 1, min(start+7, n) + 1))
        week += [None] * (7-len(week))
        yield week
        start += 7
