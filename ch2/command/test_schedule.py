
from ..command.args import SCHEDULE, MONTHS, START


def test_schedule(args, log):
    schedule, start, months = args[SCHEDULE], args[START], args[MONTHS]
    