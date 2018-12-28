
import datetime as dt

import numpy as np
from bokeh.layouts import column, row

from ch2.stoats.display.nearby import nearby_any_time
from .data_frame import interpolate_to
from .plot import dot_map, line_diff, cumulative, health, activity, heart_rate_zones
from .server import SingleShotServer
from ..data import statistics
from ..data.data_frame import set_log, session, get_log
from ..lib.date import format_time, format_seconds, local_date_to_time
from ..squeal import ActivityGroup, ActivityJournal
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.names import SPEED, DISTANCE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, TIME, FATIGUE, FITNESS, \
    REST_HR, DAILY_STEPS, ACTIVE_DISTANCE, ACTIVE_TIME, HR_ZONE

DISTANCE_KM = '%s / km' % DISTANCE
SPEED_KMH = '%s / kmh' % SPEED
HR_10 = 'HR Impulse / 10s'

LOG_FITNESS = 'Log %s' % FITNESS
LOG_FATIGUE = 'Log %s' % FATIGUE

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
  {{ caption }}
  </div>
{% endblock %}
'''


def comparison(log, s, aj1, aj2=None):

    set_log(log)
    names = [SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, SPEED, HR_ZONE, HR_10]

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
    x1, y1 = st1_10[SPHERICAL_MERCATOR_X], st1_10[SPHERICAL_MERCATOR_Y]
    if aj2:
        x2, y2 = st2_10[SPHERICAL_MERCATOR_X], st2_10[SPHERICAL_MERCATOR_Y]
    else:
        x2, y2 = None, None
    map = dot_map(side, x1, y1, st1_10['size'], x2, y2)

    y1 = st1_10[HR_10]
    y1.index = st1_10[DISTANCE_KM]  # could be left as time
    if aj2:
        y2 = st2_10[HR_10]
        y2.index = st2_10[DISTANCE_KM]
    else:
        y2 = None
    hr10_line = line_diff(700, 200, DISTANCE_KM, y1, y2)
    hr10_cumulative = cumulative(200, 200, y1, y2)

    hrz_histogram = heart_rate_zones(200, 200, st1_10[HR_ZONE])

    y1 = st1_10[DISTANCE_KM]
    c1 = st1_10[SPEED_KMH]
    if aj2:
        y2 = st2_10[DISTANCE_KM]
        c2 = st2_10[SPEED_KMH]
    else:
        c2 = None
    dist_line = line_diff(500, 200, TIME, y1, y2)
    dist_cumulative = cumulative(200, 200, c1, c2)

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

    caption = '<div><table><tr><th>Name</th><th>Date</th><th>Duration</th><th>Distance</th></tr>'
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
    caption += '</table></div>'

    SingleShotServer(log, column(row(hr10_line, hr10_cumulative),
                                 row(dist_line, dist_cumulative, hrz_histogram),
                                 row(column(health_line, activity_line),
                                     map)),
                     template=TEMPLATE, title='choochoo',
                     template_vars={
                         'header': ('%s' % aj1.name) + ((' v %s' % aj2.name) if aj2 else ''),
                         'caption': caption
                     })


if __name__ == '__main__':
    s = session('-v 5')
    day = local_date_to_time('2018-02-14')
    aj1 = s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                          ActivityJournal.start < day + dt.timedelta(days=1)).one()
    aj2 = nearby_any_time(s, aj1)[0]
    comparison(get_log(), s, aj1, aj2)
    comparison(get_log(), s, aj1, aj2)
