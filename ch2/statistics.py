

ACTIVE_DISTANCE = 'Active distance'
ACTIVE_TIME = 'Active time'
ACTIVE_SPEED = 'Active speed'
MEDIAN_KM_TIME = 'Median %dkm time'
PERCENT_IN_Z = 'Percent in Z%d'
TIME_IN_Z = 'Time in Z%d'
MAX_MED_HR_OVER_M = 'Max med HR over %dm'
HR_MINUTES = (5, 10, 15, 20, 30, 60, 90, 120, 180)

MAX = 'max'
MIN = 'min'

M = 'm'
S = 's'
KMH = 'km/h'
PC = '%'
BPM = 'bpm'


# def add_summary_stats(log, session):
#     for statistics in session.query(Statistic).all():
#         if statistics.best:
#             values = sorted(statistics.statistics, reverse=(statistics.best == 'max'), key=lambda s: s.value)
#             if values:
#                 name = '%s(%s)' % (statistics.best, statistics.name)
#                 summary = session.query(RankingStatistics).filter(RankingStatistics.name == name).one_or_none()
#                 if summary:
#                     session.delete(summary)
#                 summary = RankingStatistics(activity=statistics.activity,
#                                             activity_statistics=statistics, name=name)
#                 session.add(summary)
#                 for rank in range(min(len(values), 5)):
#                     session.add(RankingStatistic(summary_statistics=summary, activity_statistic=values[rank],
#                                                  rank=rank+1))
#                 log.info(summary)
#
#
# def add_activity_percentiles(log, session, activity):
#     for statistics in session.query(Statistic).all():
#         if statistics.best:
#             values = sorted(statistics.statistics, reverse=(statistics.best == 'max'), key=lambda s: s.value)
#             if values:
#                 name = 'Percentile(%s)' %  statistics.name
#                 statistics = session.query(Statistic).filter(Statistic.name == name).one_or_none()
#                 if statistics:
#                     session.delete(statistics)
#                 statistics = Statistic(activity=activity, units='', name=name)
#                 session.add(statistics)
#                 for rank, value in enumerate(values, start=1):
#                     percentile = 100 * rank / len(values)
#                     session.add(ActivityStatistic(activity_statistics=statistics, activity_diary=value.activity_diary,
#                                                   value=percentile))
#                 log.info(statistics)
def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)