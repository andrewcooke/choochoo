
import datetime as dt

import numpy as np
from bokeh.layouts import column, row
from bokeh.models import Div

from .data_frame import interpolate_to
from .plot import dot_map, line_diff, cumulative, health, activity, heart_rate_zones
from .server import SingleShotServer
from ..data import statistics
from ..data.data_frame import set_log, session, get_log
from ..lib.date import format_time, format_seconds, local_date_to_time
from ..squeal import ActivityGroup, ActivityJournal
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.display.nearby import nearby_any_time
from ..stoats.names import SPEED, DISTANCE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, TIME, FATIGUE, FITNESS, \
    REST_HR, DAILY_STEPS, ACTIVE_DISTANCE, ACTIVE_TIME, HR_ZONE, ELEVATION

DISTANCE_KM = '%s / km' % DISTANCE
SPEED_KPH = '%s / kph' % SPEED
ELEVATION_M = '%s / m' % ELEVATION
CLIMB_MPS = 'Climb / mps'
TIME = 'Time'
HR_10 = 'HR Impulse / 10s'

LOG_FITNESS = 'Log %s' % FITNESS
LOG_FATIGUE = 'Log %s' % FATIGUE

RIDE_PLOT_LEN = 700
RIDE_PLOT_HGT = 200

TEMPLATE = '''
{% block css_resources %}
  {{ super() }}
  <style>
body {
  background-color: white;
}
.centre {
  text-align: center
}
.centre > div {
  display: inline-block;
}
table {
  margin: 20px;
  border-spacing: 10px;
}
  </style>
{% endblock %}
{% block inner_body %}
  <div class='centre'>
  <h1>{{ header }}</h1>
  {{ super() }}
  </div>
{% endblock %}
'''


def comparison(log, s, aj1, aj2=None):

    # ---- definitions

    set_log(log)
    names = [SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, ELEVATION, SPEED, HR_ZONE, HR_10]

    # ---- load data

    def get_stats(aj):
        st = statistics(s, *names, source_ids=[aj.id])
        st[DISTANCE_KM] = st[DISTANCE]/1000
        st[SPEED_KPH] = st[SPEED] * 3.6
        st_10 = interpolate_to(st, HR_10)
        st_10.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)
        st_10[CLIMB_MPS] = st_10[ELEVATION_M].diff() * 0.1
        return st, st_10

    st1, st1_10 = get_stats(aj1)
    st2, st2_10 = get_stats(aj2) if aj2 else (None, None)

    # ---- ride-specific plots

    def ride_line(y_axis, x_axis=TIME):
        y1 = st1_10[y_axis].copy()  # copy means we don't overwrite main index
        if x_axis != TIME:
            y1.index = st1_10[x_axis]  # could be left as time
        if aj2:
            y2 = st2_10[y_axis].copy()
            if x_axis != TIME:
                y2.index = st2_10[x_axis]
        else:
            y2 = None
        return line_diff(RIDE_PLOT_LEN, RIDE_PLOT_HGT, x_axis, y1, y2)

    def ride_cum(y_axis):
        y1 = st1_10[y_axis].copy()  # copy means we don't overwrite main index
        if aj2:
            y2 = st2_10[y_axis].copy()
        else:
            y2 = None
        return cumulative(RIDE_PLOT_HGT, RIDE_PLOT_HGT, y1, y2)

    hr10_line, hr10_cumulative = ride_line(HR_10), ride_cum(HR_10)
    elvn_line, elvn_cumulative = ride_line(ELEVATION_M), ride_cum(CLIMB_MPS)
    speed_line, speed_cumulative = ride_line(SPEED_KPH), ride_cum(SPEED_KPH)

    side = 300
    mx, mn = st1_10[HR_10].max(), st1_10[HR_10].min()
    st1_10['size'] = side * ((st1_10[HR_10] - mn) / (mx - mn)) ** 3 / 10
    x1, y1 = st1_10[SPHERICAL_MERCATOR_X], st1_10[SPHERICAL_MERCATOR_Y]
    if aj2:
        x2, y2 = st2_10[SPHERICAL_MERCATOR_X], st2_10[SPHERICAL_MERCATOR_Y]
    else:
        x2, y2 = None, None
    map = dot_map(side, x1, y1, st1_10['size'], x2, y2)

    caption = '<table><tr><th>Name</th><th>Date</th><th>Duration</th><th>Distance</th></tr>'
    source_ids = [aj1.id]
    if aj2:
        source_ids.append(aj2.id)
    st = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=source_ids)
    st_aj = st.loc[st.index == aj1.start]
    caption += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f km</td></tr>' % \
               (aj1.name, format_time(aj1.start),
                format_seconds(st_aj[ACTIVE_TIME][0]), st_aj[ACTIVE_DISTANCE][0] / 1000)
    if aj2:
        st_aj = st.loc[st.index == aj2.start]
        caption += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f km</td></tr>' % \
                   (aj2.name, format_time(aj2.start),
                    format_seconds(st_aj[ACTIVE_TIME][0]), st_aj[ACTIVE_DISTANCE][0] / 1000)
    caption = Div(text=caption + '</table>', width=RIDE_PLOT_LEN, height=RIDE_PLOT_HGT)
    hrz_histogram = heart_rate_zones(RIDE_PLOT_HGT, RIDE_PLOT_HGT, st1_10[HR_ZONE])

    # ---- health-specific plots

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
               ActivityGroup.id == aj1.activity_group_id
               ).all()
    st_ac = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=[aj.id for aj in ajs])

    activity_line = activity(600, 150, st_ff[DAILY_STEPS], st_ac[ACTIVE_TIME])  # last could be distance

    # ---- display

    SingleShotServer(log, column(row(hr10_line, hr10_cumulative),
                                 row(elvn_line, elvn_cumulative),
                                 row(speed_line, speed_cumulative),
                                 row(caption, hrz_histogram),
                                 row(column(health_line, activity_line), map)),
                     template=TEMPLATE, title='choochoo',
                     template_vars={
                         'header': ('%s' % aj1.name) + ((' v %s' % aj2.name) if aj2 else '')
                     })


if __name__ == '__main__':
    s = session('-v 5')
    day = local_date_to_time('2018-03-04')
    aj1 = s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                          ActivityJournal.start < day + dt.timedelta(days=1)).one()
    aj2 = nearby_any_time(s, aj1)[0]
    comparison(get_log(), s, aj1, aj2)
