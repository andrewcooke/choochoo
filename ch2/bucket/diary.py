
import datetime as dt

import numpy as np
from bokeh.layouts import column, row, widgetbox
from bokeh.models import Div

from ch2.squeal import ActivityGroup
from .data_frame import interpolate_to
from .plot import dot_map, line_diff, cumulative, health, activity
from .server import show
from ..data import session, statistics, log
from ..lib.date import local_date_to_time, format_time, format_seconds
from ..squeal import ActivityJournal
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.display.nearby import nearby_any_time
from ..stoats.names import SPEED, DISTANCE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, TIME, FATIGUE, FITNESS, REST_HR, \
    DAILY_STEPS, ACTIVE_DISTANCE, ACTIVE_TIME

DISTANCE_KM = '%s / km' % DISTANCE
SPEED_KMH = '%s / kmh' % SPEED
HR_10 = 'HR Impulse / 10s'

LOG_FITNESS = 'Log %s' % FITNESS
LOG_FATIGUE = 'Log %s' % FATIGUE


def comparison(log, s, group, aj1, aj2=None):

    names = [SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, SPEED, HR_10]

    st1 = statistics(s, *names, source_ids=[aj1.id])
    st1[DISTANCE_KM] = st1[DISTANCE]/1000
    st1[SPEED_KMH] = st1[SPEED] * 3.6
    st1_10 = interpolate_to(st1, HR_10)

    if aj2:
        st2 = statistics(s, *names, source_ids=[aj2.id])
        st2[DISTANCE_KM] = st2[DISTANCE]/1000
        st2[SPEED_KMH] = st2[SPEED] * 3.6
        st2_10 = interpolate_to(st2, HR_10)

    side = 300
    mx, mn = st1_10[HR_10].max(), st1_10[HR_10].min()
    st1_10['size'] = side * ((st1_10[HR_10] - mn) / (mx - mn)) ** 3 / 10
    map = dot_map(side, st1_10[SPHERICAL_MERCATOR_X], st1_10[SPHERICAL_MERCATOR_Y], st1_10['size'])

    y1 = st1_10[HR_10]
    y1.index = st1_10[DISTANCE_KM]  # could be left as time
    if aj2:
        y2 = st2_10[HR_10]
        y2.index = st2_10[DISTANCE_KM]
    else:
        y2 = None
    hr10_line = line_diff(700, 200, DISTANCE_KM, y1, y2)
    hr10_cumulative = cumulative(200, 200, y1, y2)

    y1 = st1_10[DISTANCE_KM]
    c1 = st1_10[SPEED_KMH]
    if aj2:
        y2 = st2_10[DISTANCE_KM]
        c2 = st2_10[SPEED_KMH]
    else:
        c2 = None
    dist_line = line_diff(450, 150, TIME, y1, y2)
    dist_cumulative = cumulative(150, 150, c1, c2)

    finish = aj1.finish + dt.timedelta(days=1)  # to show new level
    start = finish - dt.timedelta(days=365)

    st_ff = statistics(s, FITNESS, FATIGUE, DAILY_STEPS, start=start, finish=finish)
    st_hr = statistics(s, REST_HR, owner=MonitorStatistics, start=start, finish=finish)
    st_ff[LOG_FITNESS] = np.log10(st_ff[FITNESS])
    st_ff[LOG_FATIGUE] = np.log10(st_ff[FATIGUE])

    health_line = health(600, 150, st_ff[LOG_FITNESS], st_ff[LOG_FATIGUE], st_hr[REST_HR])

    ajs = s.query(ActivityJournal). \
        join(ActivityGroup). \
        filter(ActivityJournal.start >= start,
               ActivityJournal.start < finish,
               ActivityGroup.name == group
               ).all()
    st_ac = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=[aj.id for aj in ajs])

    activity_line = activity(600, 150, st_ff[DAILY_STEPS], st_ac[ACTIVE_TIME])  # last could be distance

    at = st_ac.loc[st_ac.index == aj1.start][ACTIVE_TIME][0]
    ad = st_ac.loc[st_ac.index == aj1.start][ACTIVE_DISTANCE][0] / 1000
    comparison = ('<p>Compared to %s</p>' % format_time(aj2.start)) if aj2 else ''
    text = widgetbox(Div(text=('<p>%s</p><p>%s: %s</p><p>%s: %.2fkm</p>' + comparison) %
                              (format_time(aj1.start), ACTIVE_TIME, format_seconds(at), ACTIVE_DISTANCE, ad),
                         width=300, height=150))

    show(log, column(row(hr10_line, hr10_cumulative),
                     row(column(row(dist_line, dist_cumulative),
                                health_line,
                                activity_line),
                         column(map, text))))


if __name__ == '__main__':
    s = session('-v 5')
    day = local_date_to_time('2018-02-14')
    aj1 = s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                          ActivityJournal.start < day + dt.timedelta(days=1)).one()
    aj2 = nearby_any_time(s, aj1)[0]
    comparison(log(), s, 'Bike', aj1, aj2)
