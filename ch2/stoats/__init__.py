
from .activity import ActivityStatistics
from .summary import SummaryStatistics


def run_statistics(log, db, force=False, date=None):
    ActivityStatistics(log, db).run(force=force, date=date)
    SummaryStatistics(log, db).run(force=force, date=date)
