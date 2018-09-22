
import datetime as dt

from sqlalchemy import desc, func, asc

from .args import MONTH, YEAR, START, FORCE, ACTIVITY, FINISH
from .lib.date import to_date
from .squeal.database import Database
from .squeal.tables.activity import ActivityDiary, Activity
from .squeal.tables.statistic import Statistic
from .squeal.tables.summary import Summary, SummaryTimespan, RankingStatistic, DistributionStatistic
from .statistics import ACTIVE_DISTANCE, ACTIVE_TIME


def add_summary(args, log):
    '''
# add-summary

    ch2 add-summary ACTIVITY --month [-f]

    ch2 add-summary ACTIVITY --year [-f]

Generate summary data for the activities.  By default, if the summary already
exists, only new activities are processed.  Adding -f forces re-processing of all.

Only one period (month or year) can exist at a time; if the other is requested
the previous values are deleted.
    '''
    db = Database(args, log)
    force = args[FORCE]
    activity = args[ACTIVITY][0]
    if (args[MONTH] or args[YEAR]) and args[START]:
        raise Exception('Cannot specify start / end dates with monthly or yearly summaries')
    if not (args[MONTH] or args[YEAR] or args[START]):
        raise Exception('Specify month / year or custom date range')
    if args[START]:
        custom_summary(args[START], args[FINISH], activity, force, db, log)
    else:
        regular_summary(args[MONTH], activity, force, db, log)


def custom_summary(start, finish, activity, force, db, log):
    raise Exception('Custom summary intervals not yet supported')


def regular_summary(month, activity, force, db, log):
    type = MONTH if month else YEAR
    check_previous(type, activity, db, force, log)
    with db.session_context() as session:
        summary = Summary.from_activity_name(session, activity)
        if not summary:
            summary = Summary.new(session, activity, type)
        start = to_date(session.query(ActivityDiary).join(Activity).filter(Activity.name == activity).
                        order_by(ActivityDiary.start).limit(1).one().start)
        finish = to_date(session.query(ActivityDiary).join(Activity).filter(Activity.name == activity).
                         order_by(desc(ActivityDiary.finish)).limit(1).one().finish)
        for s, f in months(start, finish) if month else years(start, finish):
            add_range(s, f, summary, session, log)


def check_previous(type, activity, db, force, log):
    with db.session_context() as session:
        summary = Summary.from_activity_name(session, activity)
        if summary:
            if force or summary.type != type:
                log.info('Erasing previous summary data')
                session.delete(summary)


def months(start, finish):
    this_month = dt.date(start.year, start.month, 1)
    while this_month < finish:
        next_month = dt.date(this_month.year, this_month.month + 1, 1) \
            if this_month.month < 12 else dt.date(this_month.year + 1, 1, 1)
        yield this_month, next_month
        this_month = next_month


def years(start, finish):
    this_year = dt.date(start.year, 1, 1)
    while this_year < finish:
        next_year = dt.date(this_year.year + 1, 1, 1)
        yield this_year, next_year
        this_year = next_year


def add_range(start, finish, summary, session, log):
    timespan = session.query(SummaryTimespan).filter(SummaryTimespan.summary == summary,
                                                     SummaryTimespan.start == start,
                                                     SummaryTimespan.finish == finish).one_or_none()
    if timespan:
        latest = session.query(ActivityDiary).filter(ActivityDiary.date >= start,
                                                     ActivityDiary.date < finish). \
            order_by(desc(ActivityDiary.date)).limit(1).one().date
        if latest <= timespan.created:
            return  # nothing to do here
        else:
            session.delete(timespan)
    timespan = add_timespan(start, finish, summary, session, log)
    add_ranking(start, finish, timespan, session, log)


def add_timespan(start, finish, summary, session, log):
    total_activities = len(session.query(ActivityDiary).filter(
        ActivityDiary.activity == summary.activity,
        ActivityDiary.date >= start,
        ActivityDiary.date < finish
    ).all())
    if total_activities:
        total_distance = session.query(func.sum(ActivityStatistic.value)).select_from(ActivityStatistic). \
            join(ActivityDiary).join(Statistic).filter(
            Statistic.name == ACTIVE_DISTANCE,
            Statistic.activity == summary.activity,
            ActivityDiary.date >= start,
            ActivityDiary.date < finish).one()[0]
        total_time = session.query(func.sum(ActivityStatistic.value)).select_from(ActivityStatistic). \
            join(ActivityDiary).join(Statistic).filter(
            Statistic.name == ACTIVE_TIME,
            Statistic.activity == summary.activity,
            ActivityDiary.date >= start,
            ActivityDiary.date < finish).one()[0]
    else:
        total_distance, total_time = 0, 0
    timespan = SummaryTimespan(summary=summary, start=start, finish=finish, created=dt.date.today(),
                               total_time=total_time, total_distance=total_distance, total_activities=total_activities)
    session.add(timespan)
    return timespan


def add_ranking(start, finish, timespan, session, log):
    for statistic in session.query(Statistic).filter(Statistic.activity == timespan.summary.activity).all():
        if statistic.best:
            order = desc if statistic.best == 'max' else asc
            values = session.query(ActivityStatistic).join(ActivityDiary).filter(
                ActivityStatistic.statistic == statistic,
                ActivityDiary.date >= start,
                ActivityDiary.date < finish
            ).order_by(order(ActivityStatistic.value)).all()
            if values:
                n = len(values)
                for rank, value in enumerate(values, start=1):
                    percentile = 100 * (n - rank) / n
                    session.add(RankingStatistic(summary_timespan=timespan, activity_statistic=value,
                                                 rank=rank, percentile=percentile))
                if n > 4:
                    for i in range(5):
                        index = int(i * (n-1) / 4)
                        session.add(DistributionStatistic(summary_timespan=timespan, statistic=statistic,
                                                          activity_statistic=values[index],
                                                          percentile=i*25))

