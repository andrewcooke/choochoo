import datetime as dt
import time as t
from logging import getLogger

from ..json import JsonResponse
from ...diary.database import read_date, read_schedule
from ...diary.views.web import rewrite_db
from ...lib import time_to_local_time
from ...common.date import now_local, time_to_local_date, format_date
from ...lib.schedule import Schedule
from ...sql import ActivityJournal, StatisticJournal
from ...pipeline.display.activity.utils import active_days, active_months

log = getLogger(__name__)


class Diary:

    FMT = ('%Y', '%Y-%m', '%Y-%m-%d')

    @staticmethod
    def read_diary(request, s, date):
        schedule, date = parse_date(date)
        if schedule == 'd':
            data = read_date(s, date)
        else:
            data = read_schedule(s, Schedule(schedule), date)
        return rewrite_db(list(data))

    def read_neighbour_activities(self, request, s, date):
        # used in the sidebar menu to advance/retreat to the next activity
        ymd = date.count('-')
        before = ActivityJournal.before_local_time(s, date)
        after = ActivityJournal.after_local_time(s, date)
        result = {}
        if before: result['before'] = time_to_local_time(before.start, self.FMT[ymd])
        if after: result['after'] = time_to_local_time(after.start, self.FMT[ymd])
        return JsonResponse(result)

    @staticmethod
    def read_active_days(request, s, month):
        return JsonResponse(active_days(s, month))

    @staticmethod
    def read_active_months(request, s, year):
        return JsonResponse(active_months(s, year))

    @staticmethod
    def read_latest(request, s):
        latest = ActivityJournal.before_local_time(s, now_local())
        if latest: latest = format_date(time_to_local_date(latest.start))
        return JsonResponse(latest)

    @staticmethod
    def write_statistics(request, s):
        # used to write modified fields back to the database
        data = request.json
        log.info(data)
        n = 0
        for key, value in data.items():
            try:
                id = int(key)
                journal = s.query(StatisticJournal).filter(StatisticJournal.id == id).one()
                journal.set(value)
                n += 1
            except Exception as e:
                log.error(f'Could not save {key}:{value}: {e}')
        s.commit()
        log.info(f'Saved {n} values')


def parse_date(date):
    for schedule, format in (('y', '%Y'), ('m', '%Y-%m'), ('d', '%Y-%m-%d')):
        try:
            return schedule, dt.date(*t.strptime(date, format)[:3])
        except:
            pass
    raise Exception(f'Cannot parse {date}')
