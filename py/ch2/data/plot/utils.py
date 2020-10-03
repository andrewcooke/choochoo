
from colorsys import hsv_to_rgb

from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool, Range1d

from ...names import N


def tooltip(name):
    return name, '@{%s}' % name


def make_tools(y):
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (y, N.DISTANCE_KM, N.LOCAL_TIME)])]
    return tools


def make_range(column, lo=None, hi=None):
    column = column.dropna()
    mn, mx = column.min() if lo is None else lo, column.max() if hi is None else hi
    delta = mx - mn
    return Range1d(start=mn - 0.1 * delta, end=mx + 0.1 * delta)


def evenly_spaced_hues(n, saturation=1, value=1, stagger=1):
    for i in range(n):
        r, g, b = [int(x * 255) for x in hsv_to_rgb(((i * stagger) % n) / n, saturation, value)]
        yield f'#{r:02x}{g:02x}{b:02x}'.upper()


def get_renderer(f, name):
    for renderer in f.renderers:
        if renderer.name == name:
            return renderer
    raise Exception(f'No rendered {name} in {f}')
