import numpy as np
from bokeh.io import show, output_file
from bokeh.layouts import gridplot
from scipy.integrate import trapz
from scipy.interpolate import interp1d

from ch2.data import *
from ch2.data.impulse import hr_zone, impulse_10
from ch2.data.power import add_differentials, add_energy_budget, add_loss_estimate, add_power_estimate
from ch2.jupyter.decorator import template
from ch2.names import N
from ch2.pipeline.calculate.impulse import HRImpulse
from ch2.pipeline.owners import *
from ch2.sql import ActivityJournal


@template
def power_v_hr(local_time, activity_group):

    f'''
    # Power v HR ({local_time}, {activity_group})
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    local_times = ['2021-04-18 05:50:52', '2021-04-11 05:52:16', '2021-04-03 05:59:03']
    dt = 60

    s = session('-v2')
    # stats = Statistics(s, activity_journal=local_time, activity_group=activity_group, with_timespan=True)
    sources = [ActivityJournal.at(s, local_time, activity_group=activity_group) for local_time in local_times]
    stats = Statistics(s, sources=sources, with_timespan=True, with_sources=True)
    df = stats.by_name(ElevationCalculator, N.ELEVATION, N.GRADE). \
        by_name(ActivityReader, N.DISTANCE, N.SPEED, N.HEART_RATE). \
        with_.transform(N.DISTANCE, scale=1000). \
        concat(N.DISTANCE, 100). \
        concat_index(300). \
        without_sources().df
    # TODO - change default to use just the N.HR_IMPULSE_10
    fthr_df = Statistics(s).by_name(Constant, N.FTHR).df
    hr_zones = hr_zones_from_database(s, local_time, activity_group)

    hr_zone(df, fthr_df)
    ldf = linear_resample_time(df, dt=dt)
    ldf = add_differentials(ldf, max_gap=1.1 * dt)

    '''
    ## Define Model
    '''

    mass = 65 + 9
    params = {'cda': 0.42, 'crr': 0.0055, 'gamma': 2, 'zero': 2}
    bounds = {'cda': (0.1, 0.5), 'crr': (0.0, 0.01), 'gamma': (0.5, 2.5), 'zero': (1, 3)}

    def model(params, df):
        idf = impulse_10(df, HRImpulse('HR Impulse', gamma=params['gamma'], zero=params['zero'], one=6, max_secs=60))
        idf.rolling('60S').apply(lambda g: trapz(g, g.index.astype(np.int64) / 10**9))
        mdf = ldf.copy(deep=True)
        mdf[N.HR_IMPULSE_10] = interp1d(idf.index.astype(np.int64), idf[N.HR_IMPULSE_10], bounds_error=False)(mdf.index.astype(np.int64))
        mdf = add_energy_budget(mdf, mass)
        mdf = add_loss_estimate(mdf, mass, cda=params['cda'], crr=params['crr'])
        mdf = add_power_estimate(mdf)
        mdf[N.POWER_ESTIMATE].clip(lower=0, inplace=True)
        return mdf

    def cost(mdf):
        # this fits a line through the origin (the param 'zero' is the offset, effectively)
        mdf.dropna(inplace=True)
        x = np.array(mdf[N.HR_IMPULSE_10])[:, np.newaxis]
        y = mdf[N.POWER_ESTIMATE]
        _, r, _, _ = np.linalg.lstsq(x, y, rcond=None)
        return r[0]

    '''
    ## Check
    '''

    output_file(filename='/dev/null')

    def plot(mdf):

        el = comparison_line_plot(700, 200, N.DISTANCE, N.ELEVATION, mdf)
        xrange = el.x_range if el else None

        hri = comparison_line_plot(700, 200, N.DISTANCE, N.HR_IMPULSE_10, mdf, ylo=0, x_range=xrange)
        xrange = xrange or (hri.x_range if hri else None)

        hr = comparison_line_plot(700, 200, N.DISTANCE, N.HEART_RATE, mdf, x_range=xrange)
        add_hr_zones(hr, mdf, N.DISTANCE, hr_zones)
        xrange = xrange or (hr.x_range if hr else None)

        pw = comparison_line_plot(700, 200, N.DISTANCE, N.POWER_ESTIMATE, mdf, ylo=0, x_range=xrange)
        pw.varea(source=mdf, x=N.DISTANCE, y1=0, y2=N.VERTICAL_POWER,
                 level='underlay', color='black', fill_alpha=0.25)

        show(gridplot([[el], [hri], [hr], [pw]]))

    plot(model(params, df))

    '''
    ## Fit Data
    '''

    params = {'cda': 0.42, 'crr': 0.0055, 'gamma': 2, 'zero': 2}
    fit(params, df, model, cost, bounds=bounds)
    plot(model(params, df))
    params
