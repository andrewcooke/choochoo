
import datetime as dt
from calendar import day_abbr, month_abbr
from colorsys import hsv_to_rgb
from logging import getLogger

import numpy as np
import pandas as pd
from bokeh.io import show
from bokeh.models import Rect, ColumnDataSource, Circle, Arc, MultiLine, SaveTool, HoverTool, Label, Plot, Range1d, \
    Title
from bokeh.palettes import *
from math import pi

from .utils import tooltip, evenly_spaced_hues
from ...lib.data import linscale
from ...lib.date import time_to_local_time, YMD, to_time
from ...stats.names import LOCAL_TIME, DIRECTION, ASPECT_RATIO, ACTIVE_DISTANCE, TOTAL_CLIMB, like, _delta, FITNESS_D_ANY, \
    GROUP

log = getLogger(__name__)

_max, _min = max, min

CALENDAR = 'Calendar'
X, Y, XS, YS = 'X', 'Y', 'Xs', 'Ys'
ALPHA, ANGLE, ARC, COLOR, END, FILL, RADIUS, SIZE, START, WEEK, WIDTH = \
    'Alpha', 'Angle', 'Arc', 'Color', 'End', 'Fill', 'Radius', 'Size', 'Start', 'Week', 'Width'

def _cal(name): return f'{CALENDAR} {name}'

CALENDAR_X = _cal(X.upper())
CALENDAR_Y = _cal(Y.upper())
CALENDAR_XS = _cal(XS)
CALENDAR_YS = _cal(YS)
CALENDAR_ALPHA = _cal(ALPHA)
CALENDAR_ARC = _cal(ARC)
CALENDAR_ARC_RADIUS = _cal(f'{ARC} {RADIUS}')
CALENDAR_RADIUS = _cal(RADIUS)
CALENDAR_SIZE = _cal(SIZE)
CALENDAR_WEEK = _cal(WEEK)
CALENDAR_ANGLE = _cal(ANGLE)
CALENDAR_WIDTH = _cal(WIDTH)
CALENDAR_START = _cal(START)
CALENDAR_END = _cal(END)
CALENDAR_COLOR = _cal(COLOR)
CALENDAR_FILL = _cal(FILL)


K2R = [f'#{i:02x}0000'.upper() for i in range(256)]
B2R = [f'#{i:02x}00{0xff-i:02x}'.upper() for i in range(256)]
K2W = [f'#{i:02x}{i:02x}{i:02x}'.upper() for i in range(256)]


class Calendar:

    '''
    The best way to understand this is probably to see the calendar template which shows three examples.
    Or read the std_ plot definitions.

    Data are stored in the dataframe, using column names prefixed by 'Calendar'.  These can then be referred
    to when plotting (or constant values can be provided).
    '''

    def __init__(self, df, scale=13, border_day=0.25, border_month=0.4, border_year=0.4, title=None,
                 hover=None, not_hover=tuple(), all_hover=False):

        self._hover_args = (hover, not_hover, all_hover)

        start, finish = df.index.min(), df.index.max()
        start = dt.date(start.year, 1, 1)
        finish = dt.date(finish.year + 1, 1, 1) - dt.timedelta(days=1)
        delta_year = 7 * (1 + border_day) + border_year

        self._df = df
        self._df_all = pd.DataFrame(data={CALENDAR_SIZE: 1, CALENDAR_RADIUS: 0.5},
                                    index=pd.date_range(start, finish))

        self._set_date(self._df)
        self._set_xy(self._df, start, finish, border_day, border_month, delta_year)
        self._set_date(self._df_all)
        self._set_xy(self._df_all, start, finish, border_day, border_month, delta_year)

        xlo = self._df_all[CALENDAR_X].min()
        xhi = self._df_all[CALENDAR_X].max()
        ylo = self._df_all[CALENDAR_Y].min()
        yhi = self._df_all[CALENDAR_Y].max()
        nx = int(scale * (xhi - xlo))
        ny = int(scale * (yhi - ylo))

        plot = Plot(x_range=Range1d(xlo - 4, xhi + 4), y_range=Range1d(ylo - 1, yhi + 4),
                    width=nx, height=ny, title=Title(text=title))
        self._add_labels(plot, start, finish, xlo, xhi, yhi, border_day, delta_year)
        self._plot = plot

    @staticmethod
    def _set_date(df):
        df.loc[:, LOCAL_TIME] = df.index.map(lambda x: time_to_local_time(x.to_pydatetime(), YMD))

    @staticmethod
    def _set_xy(df, start, finish, border_day, border_month, delta_year):
        offset = dict((y, dt.date(year=y, month=1, day=1).weekday() - 1)
                      for y in range(start.year, finish.year+1))
        df.loc[:, CALENDAR_WEEK] = df.index.map(lambda index: (index.dayofyear + offset[index.year]) // 7)
        df.loc[:, CALENDAR_X] = df[CALENDAR_WEEK] * (1 + border_day) + df.index.month * border_month
        df.loc[:, CALENDAR_Y] = -1 * (df.index.dayofweek * (1 + border_day) +
                                      (df.index.year - start.year) * delta_year)

    @staticmethod
    def _add_labels(plot, start, finish, xlo, xhi, yhi, border_day, delta_year):
        for y in range(start.year, finish.year+1):
            plot.add_layout(Label(x=xhi + 1.1, y=(start.year - y - 0.4) * delta_year, text=str(y),
                                        text_align='center', text_baseline='bottom', angle=3*pi/2))
            for d, text in enumerate(day_abbr):
                plot.add_layout(Label(x=xlo - 1.5, y=(start.year - y) * delta_year - d * (1 + border_day),
                                      text=text, text_align='right', text_baseline='middle',
                                      text_font_size='7pt', text_color='grey'))
        dx = (xhi - xlo) / 12
        for m, text in enumerate(month_abbr[1:]):
            plot.add_layout(Label(x=xlo + dx * (m + 0.5), y=yhi + 1.5,
                                  text=text, text_align='center', text_baseline='bottom'))
        plot.toolbar.logo = None

    @staticmethod
    def _build_tools(df, hover, not_hover, all_hover):
        tools = [SaveTool()]
        if hover is None:
            hover = [col for col in df.columns if all_hover or (not col.startswith(CALENDAR) and not col in not_hover)]
        if hover:
            # names ensures that background has no hover
            tools.append(HoverTool(tooltips=[tooltip(col) for col in hover], names=['with_hover']))
        return tools

    def set_constant(self, dest, value):
        self._df.loc[:, dest] = value

    def set_linear(self, dest, name, lo=None, hi=None, min=0, max=1, gamma=1):
        self._df.loc[:, dest] = linscale(self._df[name], lo=lo, hi=hi, min=min, max=max, gamma=gamma)

    def set_size(self, name, lo=None, hi=None, min=0, max=1, gamma=1):
        self.set_linear(CALENDAR_SIZE, name, lo=lo, hi=hi, min=min, max=max, gamma=gamma)
        self._df.loc[:, CALENDAR_RADIUS] = self._df[CALENDAR_SIZE] / 2

    def set_palette(self, name, palette, lo=None, hi=None, min=0, max=1, gamma=1, nan='white'):
        n = len(palette)
        self._df.loc[:, CALENDAR_COLOR] = linscale(self._df[name], lo=lo, hi=hi, min=min, max=max, gamma=gamma). \
            map(lambda x: nan if np.isnan(x) else palette[_max(0, _min(n-1, int(x * n)))])

    def set_arc(self, angle, width, size=None, delta_radius=0, lo=0, hi=2, min=30, max=180, gamma=1):
        angle = 90 - self._df[angle]  # +ve anticlock from x
        width = linscale(self._df[width], lo=lo, hi=hi, min=min, max=max, gamma=gamma)
        self._df.loc[:, CALENDAR_START] = pi * (angle - width/2) / 180
        self._df.loc[:, CALENDAR_END] = pi * (angle + width/2) / 180
        if size is None:
            self._df.loc[:, CALENDAR_ARC_RADIUS] = self._df[CALENDAR_RADIUS]
        else:
            self._df.loc[:, CALENDAR_ARC_RADIUS] = size / 2
        self._df.loc[:, CALENDAR_ARC_RADIUS] += delta_radius

    def std_distance(self):
        self.background('square', fill_alpha=0, line_alpha=1, color='lightgrey')
        self.set_size(ACTIVE_DISTANCE, min=0.1)
        self.foreground('square', fill_alpha=1, line_alpha=0, color='black')
        self.show()

    def std_distance_climb_direction(self):
        self.background('circle', fill_alpha=1, line_alpha=0, color='#F0F0F0')
        self.set_size(ACTIVE_DISTANCE, min=0.2, max=1.1)
        self.set_palette(TOTAL_CLIMB, K2R, gamma=0.3)  # more red
        self.foreground('circle', fill_alpha=1, line_alpha=0)
        self.foreground('circle', fill_alpha=0, line_alpha=1, color='grey')
        self.set_arc(DIRECTION, ASPECT_RATIO, delta_radius=0.2)
        self.foreground('arc', fill_alpha=0, line_alpha=1, color='black')
        self.show()

    def std_distance_fitness_direction(self):
        fitness = sorted(like(_delta(FITNESS_D_ANY), self._df.columns))[0]
        self.background('circle', fill_alpha=0, line_alpha=1, color='lightgrey')
        self.set_size(ACTIVE_DISTANCE, min=0.2, max=1.1)
        self.set_palette(fitness, B2R, gamma=0.7)
        self.foreground('circle', fill_alpha=1, line_alpha=0)
        self.set_arc(DIRECTION, ASPECT_RATIO, delta_radius=0.2)
        self.foreground('arc', fill_alpha=0, line_alpha=1)
        self.show()

    def std_group_distance_climb_direction(self):
        n = int(self._df[GROUP].max()) + 1
        palette = list(evenly_spaced_hues(n, saturation=0.2, stagger=7))
        self.background('square', fill_alpha=0, line_alpha=1, color='#F0F0F0')
        self.set_palette(GROUP, palette)
        self.set_constant(CALENDAR_SIZE, 1)
        self.foreground('square', fill_alpha=1, line_alpha=0)
        self.set_size(ACTIVE_DISTANCE, min=0.2, max=0.8)
        self.set_palette(TOTAL_CLIMB, K2W, gamma=0.3)
        self.foreground('circle', fill_alpha=1, line_alpha=0)
        self.foreground('circle', fill_alpha=0, line_alpha=1, color='black')
        self.set_arc(DIRECTION, ASPECT_RATIO, delta_radius=0.2)
        self.foreground('arc', fill_alpha=0, line_alpha=1, color='black')
        self.show()

    def show(self):
        self._plot.add_tools(*self._build_tools(self._df, *self._hover_args))
        show(self._plot)

    def background(self, glyph, fill_alpha=CALENDAR_FILL, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        if glyph == 'square':
            self._rect(self._df_all, fill_alpha=fill_alpha, line_alpha=line_alpha, color=color)
        elif glyph == 'circle':
            self._circle(self._df_all, fill_alpha=fill_alpha, line_alpha=line_alpha, color=color)
        else:
            raise Exception(f'Unexpected background glyph {glyph}')

    def foreground(self, glyph, fill_alpha=CALENDAR_FILL, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        if glyph == 'square':
            self._rect(self._df, fill_alpha=fill_alpha, line_alpha=line_alpha, color=color)
        elif glyph == 'circle':
            self._circle(self._df, fill_alpha=fill_alpha, line_alpha=line_alpha, color=color)
        elif glyph == 'arc':
            self._arc(self._df, line_alpha=line_alpha, color=color)
        elif glyph == 'sqarc':
            self._sqarc(self._df, line_alpha=line_alpha, color=color)
        else:
            raise Exception(f'Unexpected foreground glyph {glyph}')

    def _rect(self, df, fill_alpha=CALENDAR_FILL, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        rect = Rect(x=CALENDAR_X, y=CALENDAR_Y, width=CALENDAR_SIZE, height=CALENDAR_SIZE,
                    fill_color=color, fill_alpha=fill_alpha,
                    line_color=color, line_alpha=line_alpha)
        return self._plot.add_glyph(ColumnDataSource(df), rect, name='with_hover' if df is self._df else None)

    def _circle(self, df, fill_alpha=CALENDAR_FILL, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        circle = Circle(x=CALENDAR_X, y=CALENDAR_Y, radius=CALENDAR_RADIUS,
                        fill_color=color, fill_alpha=fill_alpha,
                        line_color=color, line_alpha=line_alpha)
        return self._plot.add_glyph(ColumnDataSource(df), circle, name='with_hover' if df is self._df else None)

    def _arc(self, df, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        arc = Arc(x=CALENDAR_X, y=CALENDAR_Y, radius=CALENDAR_ARC_RADIUS,
                  start_angle=CALENDAR_START, end_angle=CALENDAR_END, direction='anticlock',
                  line_color=color, line_alpha=line_alpha)
        return self._plot.add_glyph(ColumnDataSource(df), arc, name='with_hover' if df is self._df else None)

    def _sqarc(self, df, line_alpha=CALENDAR_ALPHA, color=CALENDAR_COLOR):
        df = df.dropna().copy()  # copy to avoid set on view errors
        xys = list(_corners(df))
        xs, ys = list(zip(*xys))
        df.loc[:, CALENDAR_XS] = xs
        df.loc[:, CALENDAR_YS] = ys
        multi = MultiLine(xs=CALENDAR_XS, ys=CALENDAR_YS, line_color=color, line_alpha=line_alpha)
        self._plot.add_glyph(ColumnDataSource(df), multi)


# helpers for generating square arc multiline (a lot of work for not much result)

def _edge(linear, x, y, r):
    if np.isnan(linear): return x, y
    d = 2 * r * (linear - int(linear))
    if linear < 1: return x + r - d, y + r
    if linear < 2: return x - r, y + r - d
    if linear < 3: return x - r + d, y - r
    return x + r, y - r + d


def _corner(linear, x, y, r):
    if np.isnan(linear): return x, y
    if linear < 1: return x + r, y + r
    if linear < 2: return x - r, y + r
    if linear < 3: return x - r, y - r
    return x + r, y - r


def _line_corners(x, y, r, start, end):
    yield _edge(start, x, y, r)
    while start < end:
        next_corner = int(start + 1)
        if next_corner < end:
            start = next_corner
            yield _corner(start, x, y, r)
        else:
            start = end
            yield _edge(start, x, y, r)


def _linearize(angle):
    linear = (angle - pi/4) / (pi/2)
    while linear <= 0: linear += 4
    while linear > 4: linear -= 4
    return linear


def _corners(df):
    for _, row in df.iterrows():
        x, y, r = row[CALENDAR_X], row[CALENDAR_Y], row[CALENDAR_ARC_RADIUS]
        start, end = _linearize(row[CALENDAR_START]), _linearize(row[CALENDAR_END])
        xys = list(_line_corners(x, y, r, start, end))
        yield list(zip(*xys))
