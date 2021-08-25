
import datetime as dt

from IPython.core.display import display
from bokeh.io import output_file
from bokeh.layouts import row, gridplot
from bokeh.plotting import show

from ch2.data import *
from ch2.jupyter.decorator import template
from ch2.lib import *
from ch2.names import N, like
from ch2.pipeline.owners import *

@template
def activity_details(local_time, activity_group):

    f'''
    # Activity Details: {local_time} ({activity_group})
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')

    activity = std_activity_statistics(s, activity_journal=local_time, activity_group=activity_group)
    health = std_health_statistics(s)
    hr_zones = hr_zones_from_database(s, local_time, activity_group)
    climbs = Statistics(s, sources=climb_sources(s, local_time, activity_group=activity_group)). \
        by_name(SectorCalculator, N.CLIMB_ANY, N.VERTICAL_POWER, like=True).with_. \
        copy_with_units().df
    active = Statistics(s, activity_journal=local_time, activity_group=activity_group). \
        by_name(ActivityCalculator, N.ACTIVE_TIME, N.ACTIVE_DISTANCE). \
        with_.copy_with_units().df.append(climbs)

    f'''
    ## Activity Plots
    
    To the right of each plot of data against distance is a related plot of cumulative data
    (except the last, cadence, which isn't useful and so replaced by HR zones).
    Green and red areas indicate differences between the two dates. 
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_file(filename='/dev/null')

    sp = comparison_line_plot(700, 200, N.DISTANCE_KM, N.MED_SPEED_KMH, activity, ylo=0)
    add_climb_zones(sp, climbs, activity)
    sp_c = cumulative_plot(200, 200, N.MED_SPEED_KMH, activity, ylo=0)
    xrange = sp.x_range if sp else None

    el = comparison_line_plot(700, 200, N.DISTANCE_KM, N.ELEVATION_M, activity, x_range=xrange)
    add_climbs(el, climbs, activity)
    el_c = cumulative_plot(200, 200, N.CLIMB_MS, activity)
    xrange = xrange or (el.x_range if el else None)

    hri = comparison_line_plot(700, 200, N.DISTANCE_KM, N.HR_IMPULSE_10, activity, ylo=0, x_range=xrange)
    add_climb_zones(hri, climbs, activity)
    hri_c = cumulative_plot(200, 200, N.HR_IMPULSE_10, activity, ylo=0)
    xrange = xrange or (hri.x_range if hri else None)

    hr = comparison_line_plot(700, 200, N.DISTANCE_KM, N.HEART_RATE_BPM, activity, x_range=xrange)
    add_hr_zones(hr, activity, N.DISTANCE_KM, hr_zones)
    add_climb_zones(hr, climbs, activity)
    hr_c = cumulative_plot(200, 200, N.HEART_RATE_BPM, activity)
    xrange = xrange or (hr.x_range if hr else None)

    pw = comparison_line_plot(700, 200, N.DISTANCE_KM, N.MED_POWER_ESTIMATE_W, activity, ylo=0, x_range=xrange)
    pw.varea(source=activity, x=N.DISTANCE_KM, y1=0, y2=N.MED_VERTICAL_POWER_W,
             level='underlay', color='black', fill_alpha=0.25)
    add_climb_zones(pw, climbs, activity)
    pw_c = cumulative_plot(200, 200, N.MED_POWER_ESTIMATE_W, activity, ylo=0)
    xrange = xrange or (pw.x_range if pw else None)

    cd = comparison_line_plot(700, 200, N.DISTANCE_KM, N.MED_CADENCE_RPM, activity, ylo=0, x_range=xrange)
    add_climb_zones(cd, climbs, activity)
    hr_h = histogram_plot(200, 200, N.HR_ZONE, activity, xlo=1, xhi=5)

    show(gridplot([[el, el_c], [sp, sp_c], [hri, hri_c], [hr, hr_c], [pw, pw_c], [cd, hr_h]]))

    '''
    ## Activity Maps
    '''

    map = map_plot(400, 400, activity)
    m_el = map_intensity_signed(200, 200, activity, N.GRADE_PC, ranges=map, power=0.5)
    m_sp = map_intensity(200, 200, activity, N.MED_SPEED_KMH, ranges=map, power=2)
    m_hr = map_intensity(200, 200, activity, N.HR_IMPULSE_10, ranges=map)
    m_pw = map_intensity(200, 200, activity, N.MED_POWER_ESTIMATE_W, ranges=map)
    show(row(map, gridplot([[m_el, m_sp], [m_hr, m_pw]], toolbar_location='right')))

    '''
    ## Activity Statistics
    '''

    '''
    Active time and distance exclude pauses.
    '''

    active[[N.ACTIVE_TIME_S, N.ACTIVE_DISTANCE_KM]].dropna(). \
        transform({N.ACTIVE_TIME_S: format_seconds, N.ACTIVE_DISTANCE_KM: format_km})

    '''
    Climbs are auto-detected and shown only for the main activity. They are included in the elevation plot above.
    '''

    if present(climbs, N.CLIMB_TIME):
        display(transform(climbs,
                          {N.CLIMB_TIME: format_seconds, N.CLIMB_ELEVATION: format_metres,
                           N.CLIMB_DISTANCE: format_km, N.CLIMB_GRADIENT: format_percent,
                           N.VERTICAL_POWER: format_watts, N.CLIMB_CATEGORY: lambda x: x}))

    '''
    ## Health and Fitness
    '''

    fitness, fatigue = like(N.FITNESS_ANY, health.columns), like(N.FATIGUE_ANY, health.columns)
    colours = ['black'] * len(fitness) + ['red'] * len(fatigue)
    alphas = [1.0] * len(fitness) + [0.5] * len(fatigue)
    ff = multi_line_plot(900, 300, N.TIME, fitness + fatigue, health, colours, alphas=alphas)
    xrange = ff.x_range if ff else None
    add_multi_line_at_index(ff, N.TIME, fitness + fatigue, health, colours, alphas=alphas, index=-1)
    atd = std_distance_time_plot(900, 200, health, x_range=xrange)
    show(gridplot([[ff], [atd]]))
