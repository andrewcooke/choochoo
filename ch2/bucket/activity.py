
import datetime as dt
from time import sleep

import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import Div

from .data_frame import interpolate_to, add_interpolation
from .plot import line_diff, cumulative, heart_rate_zones, line_diff_elevation_climbs, dot_map, activities, health
from .server import Page, singleton_server
from ..config import config
from ..data.data_frame import set_log, activity_statistics, statistics
from ..lib.date import format_seconds, time_to_local_time, to_time
from ..squeal import ActivityJournal, StatisticJournal, ActivityGroup
from ..stoats.calculate.activity import ActivityStatistics
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.display.climb import climbs_for_activity
from ..stoats.display.segment import segments_for_activity
from ..stoats.names import SPEED, DISTANCE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, TIME, FATIGUE, FITNESS, \
    ACTIVE_DISTANCE, ACTIVE_TIME, HR_ZONE, ELEVATION, CLIMB_ELEVATION, CLIMB_DISTANCE, ALTITUDE, \
    CLIMB_TIME, CLIMB_GRADIENT, LOCAL_TIME, DAILY_STEPS, REST_HR

WINDOW = '60s'
#WINDOW = 10
MIN_PERIODS = 1

INTERPOLATION = 'interpolation'

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


def caption(s, activity):

    active_distance = StatisticJournal.for_source(s, activity.id, ACTIVE_DISTANCE,
                                                  ActivityStatistics, activity.activity_group).value
    active_time = StatisticJournal.for_source(s, activity.id, ACTIVE_TIME,
                                              ActivityStatistics, activity.activity_group).value
    total_time = (activity.finish - activity.start).total_seconds()
    local_start = time_to_local_time(activity.start)
    local_finish = time_to_local_time(activity.finish)
    text = f'{local_start.strftime("%Y-%m-%d")}: ' \
        f'{local_start.strftime("%H:%M:%S")}-{local_finish.strftime("%H:%M:%S")} ' \
        f'{format_seconds(active_time)}/{format_seconds(total_time)} ' \
        f'{active_distance/1000:.2f}km'

    total_climb, climbs = climbs_for_activity(s, activity)
    if total_climb:
        extra = f'{int(total_climb.value):d}m:'
        extra += ','.join(f' {int(climb[CLIMB_ELEVATION].value)}m '
                          f'in {format_seconds(climb[CLIMB_TIME].value)} '
                          f'at {climb[CLIMB_GRADIENT].value:.1f}%'
                          for climb in climbs)
        text += '</br>' + extra

    segments = segments_for_activity(s, activity)
    if segments:
        extra = ', '.join(f'{segment.segment.name} in '
                          f'{format_seconds((segment.finish - segment.start).total_seconds())}'
                          for segment in segments)
        text += '</br>' + extra

    return text


def comparison(log, s, activity, compare=None):

    # ---- definitions

    set_log(log)
    names = [SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, ELEVATION, SPEED, HR_ZONE, HR_10, ALTITUDE]

    # ---- load data

    def get_stats(aj):
        st = [df for id, df in
              activity_statistics(s, *names, activity_journal_id=aj.id, with_timespan=True).groupby('timespan_id')]
        for df in st:
            df[TIME] = df.index
            # this seems to be a bug in pandas not supporting astimezone for some weird internal datetime
            df[LOCAL_TIME] = df[TIME].apply(lambda x: time_to_local_time(to_time(x.timestamp())).strftime('%H:%M:%S'))
            df[DISTANCE_KM] = df[DISTANCE]/1000
            df[SPEED_KPH] = df[SPEED] * 3.6
            df[MED_SPEED_KPH] = df[SPEED].rolling(WINDOW, min_periods=MIN_PERIODS).median() * 3.6
            df[MED_HR_10] = df[HR_10].rolling(WINDOW, min_periods=1).median()
            df.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)
        st = [add_interpolation(INTERPOLATION, df, HR_10, 10) for df in st]
        st_10 = [interpolate_to(df, INTERPOLATION) for df in st]
        for df in st_10:
            df[CLIMB_MPS] = df[ELEVATION_M].diff() * 0.1
        return st, st_10

    st1, st1_10 = get_stats(activity)
    st2, st2_10 = get_stats(compare) if compare else (None, None)
    climbs = activity_statistics(s, CLIMB_DISTANCE, CLIMB_ELEVATION, activity_journal_id=activity.id)
    line_x_range = None

    def build(st, *axes):
        axes = list(axes) + [LOCAL_TIME]
        return [df.loc[:, axes] for df in st]

    def build_all(*axes):
        source1 = build(st1_10, *axes)
        source2 = build(st2_10, *axes) if compare else None
        return source1, source2

    # def all_frames(st, name):
    #     return [df[name].copy() for df in st]
    #
    # def set_axis(ys, st, name):
    #     if name != TIME:
    #         for y, df in zip(ys, st):
    #             y.index = df[name].copy()

    # ---- ride-specific plots

    # def set_axes(y_axis, x_axis=TIME):
    #     y1 = all_frames(st1_10, y_axis)
    #     set_axis(y1, st1_10, x_axis)
    #     if compare:
    #         y2 = all_frames(st2_10, y_axis)
    #         set_axis(y2, st2_10, x_axis)
    #     else:
    #         y2 = None
    #     return y1, y2

    def ride_line(y_axis, x_axis=TIME):
        source1, source2, = build_all(x_axis, y_axis)
        return line_diff(RIDE_PLOT_LEN, RIDE_PLOT_HGT, x_axis, y_axis, source1, source2, x_range=line_x_range)

    def ride_elevn(x_axis=TIME):
        source1, source2, = build_all(x_axis, ELEVATION_M, ALTITUDE)
        return line_diff_elevation_climbs(RIDE_PLOT_LEN, RIDE_PLOT_HGT, x_axis, ELEVATION_M, source1, source2,
                                          climbs=climbs, st=st1, x_range=line_x_range)

    def ride_cum(y_axis):
        source1, source2 = build_all(y_axis)
        return cumulative(RIDE_PLOT_HGT, RIDE_PLOT_HGT, pd.concat(df[y_axis] for df in source1),
                          pd.concat(df[y_axis] for df in source2) if compare else None)

    hr10_line = ride_line(MED_HR_10, x_axis=DISTANCE_KM)
    hr10_cumulative = ride_cum(HR_10)
    if hr10_line.tools:  # avoid if HR not available
        line_x_range = hr10_line.x_range
    elvn_line = ride_elevn(x_axis=DISTANCE_KM)
    elvn_cumulative = ride_cum(CLIMB_MPS)
    if line_x_range is None and elvn_line.tools:
        line_x_range = elvn_line.x_range
    speed_line = ride_line(MED_SPEED_KPH, x_axis=DISTANCE_KM)
    speed_cumulative = ride_cum(SPEED_KPH)

    hr10 = build(st1_10, HR_10)
    if hr10:
        hr10 = pd.concat(hr10)
        mn, mx = hr10.quantile(0.1)[0], hr10.quantile(0.95)[0]
        for df in st1_10:
            df['size'] = MAP_LEN * ((df[HR_10] - mn) / (mx - mn)) ** 2 / 10
    else:
        for df in st1_10:
            df['size'] = df[SPHERICAL_MERCATOR_X] * 0
    xy1 = build(st1_10, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, 'size', DISTANCE_KM)
    if compare:
        xy2 = build(st2_10, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE_KM)
    else:
        xy2 = None
    map = dot_map(MAP_LEN, xy1, xy2)

    p = '<p>%s</p>' % caption(s, activity)
    if compare:
        p += '<p>%s</p>' % caption(s, compare)
    text = Div(text=p, width=RIDE_PLOT_LEN, height=RIDE_PLOT_HGT)

    hrz_histogram = heart_rate_zones(RIDE_PLOT_HGT, RIDE_PLOT_HGT, pd.concat([df[HR_ZONE] for df in st1_10]))

    # ---- health-specific plots

    finish = activity.finish + dt.timedelta(days=1)  # to show new level
    start = finish - dt.timedelta(days=365)
    line_x_range = None

    st_ff = statistics(s, FITNESS, FATIGUE, DAILY_STEPS, start=start, finish=finish)
    st_ff[TIME] = st_ff.index
    st_ff[LOCAL_TIME] = st_ff[TIME].apply(lambda x: time_to_local_time(to_time(x.timestamp())).strftime('%Y-%m-%d'))
    st_hr = statistics(s, REST_HR, owner=MonitorStatistics, start=start, finish=finish)
    st_ff[LOG_FITNESS] = np.log10(st_ff[FITNESS])
    st_ff[LOG_FATIGUE] = np.log10(st_ff[FATIGUE])

    health_line = health(HEALTH_PLT_LEN, HEALTH_PLOT_HGT, st_ff, st_hr, x_range=line_x_range)
    if health_line.tools:
        line_x_range = health_line.x_range

    ajs = s.query(ActivityJournal). \
        join(ActivityGroup). \
        filter(ActivityJournal.start >= start,
               ActivityJournal.start < finish,
               ActivityGroup.id == activity.activity_group_id
               ).all()
    st_ac = statistics(s, ACTIVE_TIME, ACTIVE_DISTANCE, source_ids=[aj.id for aj in ajs])

    activity_line = activities(HEALTH_PLT_LEN, HEALTH_PLOT_HGT, get(st_ff, DAILY_STEPS), st_ac[ACTIVE_TIME],
                               x_range=line_x_range)

    # ---- the final mosaic of plots

    return column(row(hr10_line, hr10_cumulative),
                  row(elvn_line, elvn_cumulative),
                  row(speed_line, speed_cumulative),
                  row(text, hrz_histogram),
                  row(column(health_line, activity_line), map)
                  )


class ActivityJournalPage(Page):

    def create(self, s, id=None, compare=None, **kargs):
        aj1 = s.query(ActivityJournal). \
            filter(ActivityJournal.id == self.single_int_param('id', id)).one()
        title = aj1.name
        if compare:
            aj2 = s.query(ActivityJournal). \
                filter(ActivityJournal.id == self.single_int_param('compare', compare)).one()
            title += ' v ' + aj2.name
        else:
            aj2 = None
        return {'header': title, 'title': title}, comparison(self._log, s, aj1, aj2)


if __name__ == '__main__':
    log, db = config('-v 5')
    server = singleton_server(log, {'/activity_journal': ActivityJournalPage(log, db)})
    try:
        with db.session_context() as s:
            # aj1 = ActivityJournal.at_date(s, '2019-01-25')[0]
            # aj2 = ActivityJournal.at_date(s, '2019-01-23')[0]
            # path = '/activity_journal?id=%d&compare=%d' % (aj1.id, aj2.id)
            aj1 = ActivityJournal.at_date(s, '2018-03-04')[0]
            path = '/activity_journal?id=%d' % aj1.id
            server.show(path)
        print('Crtl-C')
        while True:
            sleep(1)
    finally:
        server.stop()
