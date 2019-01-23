
import datetime as dt

import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import Div

from .data_frame import interpolate_to
from .plot import dot_map, line_diff, cumulative, heart_rate_zones, health, line_diff_elevation_climbs, \
    max_all, min_all, activities
from .server import Page
from ..data import statistics
from ..data.data_frame import set_log, activity_statistics
from ..lib.date import format_time, format_seconds
from ..squeal import ActivityGroup
from ..squeal import ActivityJournal
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.names import SPEED, DISTANCE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, TIME, FATIGUE, FITNESS, \
    ACTIVE_DISTANCE, ACTIVE_TIME, HR_ZONE, ELEVATION, REST_HR, DAILY_STEPS, CLIMB_ELEVATION, CLIMB_DISTANCE, ALTITUDE

WINDOW = '60s'
#WINDOW = 10
MIN_PERIODS = 1

DISTANCE_KM = '%s / km' % DISTANCE
SPEED_KPH = '%s / kph' % SPEED
MED_SPEED_KPH = 'M(%s) %s / kph' % (WINDOW, SPEED)
ELEVATION_M = '%s / m' % ELEVATION
CLIMB_MPS = 'Climb / mps'
HR_10 = 'HR Impulse / 10s'
MED_HR_10 = 'M(%s) HR Impulse / 10s' % WINDOW

LOG_FITNESS = 'Log %s' % FITNESS
LOG_FATIGUE = 'Log %s' % FATIGUE

RIDE_PLOT_LEN = 700
RIDE_PLOT_HGT = 200
HEALTH_PLT_LEN = 500
HEALTH_PLOT_HGT = 200
MAP_LEN = 400


def get(df, name):
    if name in df:
        return df[name]
    else:
        return None


def comparison(log, s, activity, compare=None):

    # ---- definitions

    set_log(log)
    names = [SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, ELEVATION, SPEED, HR_ZONE, HR_10, ALTITUDE]

    # ---- load data

    def get_stats(aj):
        st = [df for id, df in
              activity_statistics(s, *names, activity_journal_id=aj.id, with_timespan=True).groupby('timespan_id')]
        for df in st:
            df[DISTANCE_KM] = df[DISTANCE]/1000
            df[SPEED_KPH] = df[SPEED] * 3.6
            df[MED_SPEED_KPH] = df[SPEED].rolling(WINDOW, min_periods=MIN_PERIODS).median() * 3.6
            df[MED_HR_10] = df[HR_10].rolling(WINDOW, min_periods=1).median()
            df.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)
        st_10 = [interpolate_to(df, HR_10) for df in st]
        for df in st_10:
            df[CLIMB_MPS] = df[ELEVATION_M].diff() * 0.1
        return st, st_10

    st1, st1_10 = get_stats(activity)
    st2, st2_10 = get_stats(compare) if compare else (None, None)
    climbs = activity_statistics(s, CLIMB_DISTANCE, CLIMB_ELEVATION, activity_journal_id=activity.id)
    line_x_range = None

    def all_frames(st, name):
        return [df[name].copy() for df in st]

    def set_axis(ys, st, name):
        if name != TIME:
            for y, df in zip(ys, st):
                y.index = df[name].copy()

    # ---- ride-specific plots

    def set_axes(y_axis, x_axis=TIME):
        y1 = all_frames(st1_10, y_axis)
        set_axis(y1, st1_10, x_axis)
        if compare:
            y2 = all_frames(st2_10, y_axis)
            set_axis(y2, st2_10, x_axis)
        else:
            y2 = None
        return y1, y2

    def ride_line(y_axis, x_axis=TIME):
        y1, y2 = set_axes(y_axis, x_axis=x_axis)
        return line_diff(RIDE_PLOT_LEN, RIDE_PLOT_HGT, x_axis, y1, y2, x_range=line_x_range)

    def ride_elevn(x_axis=TIME):
        y1, y2 = set_axes(ELEVATION_M, x_axis=x_axis)
        y3, _ = set_axes(ALTITUDE, x_axis=x_axis)
        return line_diff_elevation_climbs(RIDE_PLOT_LEN, RIDE_PLOT_HGT, y1, y2, climbs=climbs, st=st1, y3=y3,
                                          x_range=line_x_range)

    def ride_cum(y_axis):
        y1 = all_frames(st1_10, y_axis)
        if compare:
            y2 = all_frames(st2_10, y_axis)
        else:
            y2 = None
        return cumulative(RIDE_PLOT_HGT, RIDE_PLOT_HGT, y1, y2)

    hr10_line, hr10_cumulative = ride_line(MED_HR_10, x_axis=DISTANCE_KM), ride_cum(HR_10)
    line_x_range = hr10_line.x_range
    elvn_line, elvn_cumulative = ride_elevn(x_axis=DISTANCE_KM), ride_cum(CLIMB_MPS)
    speed_line, speed_cumulative = ride_line(MED_SPEED_KPH, x_axis=DISTANCE_KM), ride_cum(SPEED_KPH)

    mx, mn = max_all(df[HR_10] for df in st1_10), min_all(df[HR_10] for df in st1_10),
    for df in st1_10:
        df['size'] = MAP_LEN * ((df[HR_10] - mn) / (mx - mn)) ** 3 / 10
    x1, y1 = all_frames(st1_10, SPHERICAL_MERCATOR_X), all_frames(st1_10, SPHERICAL_MERCATOR_Y)
    if compare:
        x2, y2 = all_frames(st2_10, SPHERICAL_MERCATOR_X), all_frames(st2_10, SPHERICAL_MERCATOR_Y)
    else:
        x2, y2 = None, None
    map = dot_map(MAP_LEN, x1, y1, [df['size'] for df in st1_10], x2, y2)

    caption = '<table><tr><th>Name</th><th>Date</th><th>Duration</th><th>Distance</th></tr>'
    source_ids = [activity.id]
    if compare:
        source_ids.append(compare.id)
    st = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=source_ids)
    st_aj = st.loc[st.index == activity.start]
    caption += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f km</td></tr>' % \
               (activity.name, format_time(activity.start),
                format_seconds(st_aj[ACTIVE_TIME][0]), st_aj[ACTIVE_DISTANCE][0] / 1000)
    if compare:
        st_aj = st.loc[st.index == compare.start]
        caption += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f km</td></tr>' % \
                   (compare.name, format_time(compare.start),
                    format_seconds(st_aj[ACTIVE_TIME][0]), st_aj[ACTIVE_DISTANCE][0] / 1000)
    caption = Div(text=caption + '</table>', width=RIDE_PLOT_LEN, height=RIDE_PLOT_HGT)

    hrz_histogram = heart_rate_zones(RIDE_PLOT_HGT, RIDE_PLOT_HGT, pd.concat([df[HR_ZONE] for df in st1_10]))

    # ---- health-specific plots

    finish = activity.finish + dt.timedelta(days=1)  # to show new level
    start = finish - dt.timedelta(days=365)

    st_ff = statistics(s, FITNESS, FATIGUE, DAILY_STEPS, start=start, finish=finish)
    st_hr = statistics(s, REST_HR, owner=MonitorStatistics, start=start, finish=finish)
    st_ff[LOG_FITNESS] = np.log10(st_ff[FITNESS])
    st_ff[LOG_FATIGUE] = np.log10(st_ff[FATIGUE])

    health_line = health(HEALTH_PLT_LEN, HEALTH_PLOT_HGT, st_ff[LOG_FITNESS], st_ff[LOG_FATIGUE], st_hr[REST_HR])

    ajs = s.query(ActivityJournal). \
        join(ActivityGroup). \
        filter(ActivityJournal.start >= start,
               ActivityJournal.start < finish,
               ActivityGroup.id == activity.activity_group_id
               ).all()
    st_ac = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=[aj.id for aj in ajs])

    activity_line = activities(HEALTH_PLT_LEN, HEALTH_PLOT_HGT, get(st_ff, DAILY_STEPS), st_ac[ACTIVE_TIME])  # last could be distance

    # ---- the final mosaic of plots

    return column(row(hr10_line, hr10_cumulative),
                  row(elvn_line, elvn_cumulative),
                  row(speed_line, speed_cumulative),
                  row(caption, hrz_histogram),
                  row(column(health_line, activity_line), map))


class DiaryPage(Page):

    def create(self, s, activity=None, compare=None, **kargs):
        aj1 = s.query(ActivityJournal).filter(ActivityJournal.id ==
                                              self.single_int_param('activity', activity)).one()
        title = aj1.name
        if compare:
            aj2 = s.query(ActivityJournal).filter(ActivityJournal.id ==
                                                  self.single_int_param('compare', compare)).one()
            title += ' v ' + aj2.name
        else:
            aj2 = None
        return {'header': title, 'title': title}, comparison(self._log, s, aj1, aj2)
