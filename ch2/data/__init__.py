
from .frame import df, session, statistics, statistic_quartiles, activity_statistics, std_activity_statistics, \
    std_health_statistics, nearby_activities, bookmarks, statistic_names, statistics, present
from .power import fit_power
from ch2.data.frame import linear_resample_time
from .heart_rate import *
from .plot import col_to_boxstats, box_plot, line_plotter, dot_plotter, bar_plotter, add_climbs, multi_plot, \
    multi_dot_plot, multi_bar_plot, multi_line_plot, map_thumbnail, map_intensity, map_plot, histogram_plot, \
    cumulative_plot, tile, comparison_line_plot
from .lib import chisq, fit, inplace_decay
from .text import *
from ..stoats.display.nearby import nearby_earlier, nearby_any_time
from ..stoats.names import *

# avoid cleaning of imports
nearby_earlier, nearby_any_time, CLIMB_DISTANCE
