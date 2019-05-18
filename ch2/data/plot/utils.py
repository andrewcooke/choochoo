
from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool

from ...stoats.names import DISTANCE_KM, LOCAL_TIME


def tooltip(name):
    return name, '@{%s}' % name


def make_tools(y):
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (y, DISTANCE_KM, LOCAL_TIME)])]
    return tools
