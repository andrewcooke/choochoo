
from collections import namedtuple
from logging import getLogger
from math import pi

# hide from imports of this package
import numpy as _np
import pandas as _pd
import scipy as _sp

from .frame import median_dt, session, activity_statistics, bookmarks
from .lib import fit, inplace_decay
from ..lib.data import tmp_name
from ..names import _delta, _avg, _sqr
from ..names import Names

log = getLogger(__name__)
RAD_TO_DEG = 180 / pi


def add_differentials(df, max_gap=None):
    return _add_differentials(df, Names.SPEED, Names.DISTANCE, Names.ELEVATION, Names.SPEED, Names.SPEED_2,
                              Names.LATITUDE, Names.LONGITUDE, max_gap=max_gap)


def add_air_speed(df, wind_speed=0, wind_heading=0, max_gap=None):
    df[Names.AIR_SPEED] = df[Names.SPEED] + wind_speed * _np.cos((df[Names.HEADING] - wind_heading) / RAD_TO_DEG)
    return _add_differentials(df, Names.AIR_SPEED, Names.AIR_SPEED, max_gap=max_gap)


def _add_differentials(df, speed, *names, max_gap=None):

    # rather than use timespans (old approach) it's more reliable to discard any intervals
    # over a certain time gap.

    speed_2 = _sqr(speed)
    df[speed_2] = df[speed] ** 2

    tmp = tmp_name()
    df[tmp] = df.index
    df[tmp] = df[tmp].diff().dt.seconds

    for name in names:
        df[_delta(name)] = df[name].diff()
        df.loc[df[tmp] > max_gap, [_delta(name)]] = _np.nan

    if Names.LATITUDE in names and Names.LONGITUDE in names and Names.HEADING not in df.columns:
        df[Names.HEADING] = _np.arctan2(df[_delta(Names.LONGITUDE)], df[_delta(Names.LATITUDE)]) * RAD_TO_DEG
        df.loc[df[tmp] > max_gap, [Names.HEADING]] = _np.nan

    avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(df[speed], df[speed][1:])]
    df[_avg(speed_2)] = [_np.nan] + avg_speed_2
    if max_gap:
        df.loc[df[tmp] > max_gap, [_avg(speed_2)]] = _np.nan

    df.drop(columns=[tmp], inplace=True)
    return df


def _add_differentials_old(df, speed, *names):

    # todo - remove once we've checked power calcs

    speed_2 = _sqr(speed)
    df[speed_2] = df[speed] ** 2

    def diff():
        for _, old_span in df.groupby(Names.TIMESPAN_ID):
            # discard leading and trailing na
            subset = old_span[list(names)].isna().any(axis=1).replace(True, _np.nan)
            start, finish = subset.first_valid_index(), subset.last_valid_index()
            if start and finish:
                old_span = old_span.loc[start:finish]

                if all(len(old_span[name]) == len(old_span[name].dropna()) for name in names):
                    new_span = _pd.DataFrame(index=old_span.index)
                    for col in names:
                        new_span[_delta(col)] = old_span[col].diff()
                    if Names.HEADING not in old_span.columns:
                        new_span[Names.HEADING] = _np.arctan2(new_span[_delta(Names.LONGITUDE)], new_span[_delta(Names.LATITUDE)]) * RAD_TO_DEG
                    avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(old_span[speed], old_span[speed][1:])]
                    new_span[_avg(speed_2)] = [_np.nan] + avg_speed_2
                    yield new_span

    spans = list(diff())
    if len(spans):
        extra = _pd.concat(spans).sort_index()
        return df.drop(columns=list(extra.columns), errors='ignore').join(extra)
    else:
        raise PowerException('Missing data - found no spans without NANs')


def add_energy_budget(df, m, g=9.8):
    # if DELTA_ELEVATION is +ve we've gone uphill.  so this is the total amount of energy
    # gained in this segment.
    df[Names.DELTA_ENERGY] = m * (df[Names.DELTA_SPEED_2] / 2 + df[Names.DELTA_ELEVATION] * g)
    return df


def add_cda_estimate(df, p=1.225):
    # https://www.cyclingpowerlab.com/CyclingAerodynamics.aspx
    # assume that all energy lost (-ve gain) is due to air resistance.
    df[Names.CDA] = -df[Names.DELTA_ENERGY] / (p * df[Names.AVG_AIR_SPEED_2] * df[Names.DELTA_DISTANCE] * 0.5)
    return df


def add_crr_estimate(df, m, g=9.8):
    # assume that all energy lost is due to rolling resistance
    df[Names.CRR] = -df[Names.DELTA_ENERGY] / (df[Names.DELTA_DISTANCE] * m * g)
    return df


def add_loss_estimate(df, m, cda=0.45, crr=0, p=1.225, g=9.8):
    # this is the energy spent on air and rolling resistance
    df[Names.LOSS] = (cda * p * df[Names.AVG_AIR_SPEED_2] * 0.5 + crr * m * g) * df[Names.DELTA_DISTANCE]
    return df


def add_power_estimate(df):
    # power input must balance the energy budget.
    df[Names.POWER_ESTIMATE] = (df[Names.DELTA_ENERGY] + df[Names.LOSS]) / df[Names.DELTA_TIME].dt.total_seconds()
    df[Names.POWER_ESTIMATE].clip(lower=0, inplace=True)
    if Names.CADENCE in df.columns: df.loc[df[Names.CADENCE] < 1, [Names.POWER_ESTIMATE]] = 0
    df.loc[df[Names.POWER_ESTIMATE].isna(), [Names.POWER_ESTIMATE]] = 0
    energy = (df[Names.POWER_ESTIMATE].iloc[1:] * df[Names.DELTA_TIME].iloc[1:]).cumsum()
    df[Names.ENERGY] = 0
    df.loc[1:, [Names.ENERGY]] = energy
    return df


def add_modeled_hr(df, window, slope, delay):
    dt = median_dt(df)
    window, delay = int(0.5 + window / dt), delay / dt
    df[Names.DETRENDED_HEART_RATE] = df[Names.HEART_RATE] - df[Names.HEART_RATE].rolling(window, center=True, min_periods=1).median()
    df[Names.PREDICTED_HEART_RATE] = df[Names.POWER_ESTIMATE] * slope
    inplace_decay(df, Names.PREDICTED_HEART_RATE, delay)
    df[Names.PREDICTED_HEART_RATE] -= df[Names.PREDICTED_HEART_RATE].rolling(window, center=True, min_periods=1).median()
    return df


def measure_initial_delay(df, dt=None, col1=Names.HEART_RATE, col2=Names.POWER_ESTIMATE, n=20):
    dt = dt or median_dt(df)
    correln = [(i, df[col1].corr(df[col2].shift(freq=f'{i * dt}S'))) for i in range(-n, n + 1)]
    correln = sorted(correln, key=lambda c: c[1], reverse=True)
    return dt * correln[0][0]


def measure_initial_scaling(df):
    delay = measure_initial_delay(df)
    if delay < 0: raise PowerException('Cannot estimate delay (insufficient data?)')
    df[Names.DELAYED_POWER] = df[Names.POWER_ESTIMATE].shift(freq=f'{delay}S')
    clean = df.loc[:, (Names.DELAYED_POWER, Names.HEART_RATE)].dropna()
    fit = _sp.stats.linregress(x=clean[Names.DELAYED_POWER], y=clean[Names.HEART_RATE])
    log.debug(f'Initial fit {fit}')
    return fit.slope, fit.intercept,  delay


class PowerException(Exception): pass


# the 13.5 delay is from fitting my rides til 2019
# it seems oddly low to me - i wonder if i have an error confusing bins and time
PowerModel = namedtuple('PowerModel', 'cda, crr, slope, window, delay, m,  wind_speed, wind_heading',
                        defaults=[0.5, 0,   200,   60*60,  13.5,  70, 0,          0])


def evaluate(df, model, quiet=True):
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, model.m)
    df = add_air_speed(df, model.wind_speed, model.wind_heading)
    df = add_loss_estimate(df, model.m, cda=model.cda, crr=model.crr)
    df = add_power_estimate(df)
    return df


MIN_DELAY = 1


def fit_power(df, model, *vary, tol=0.1):

    log.debug(f'Fit power: varying {vary}')
    df = evaluate(df, model)
    slope, intercept, delay = measure_initial_scaling(df)
    # we ignore intercept because removing the median makes it very weakly constrained
    model = model._replace(slope=slope, delay=delay)
    log.debug(f'Fit power: initial model {model}')

    # the internal delay is continuous
    # model delay is MIN_DELAY when the internal delay is zero, and otherwise increases

    def forwards(kargs):
        if 'delay' in kargs:
            kargs['delay'] = kargs['delay'] - MIN_DELAY
        return kargs

    def backwards(kargs):
        if 'delay' in kargs:
            kargs['delay'] = abs(kargs['delay']) + MIN_DELAY
        return kargs

    def evaluate_and_extend(df, model):
        df = evaluate(df, model)
        df = add_modeled_hr(df, model.window, model.slope, model.delay)
        return df

    model = fit(Names.DETRENDED_HEART_RATE, Names.PREDICTED_HEART_RATE, df, model, evaluate_and_extend,
                *vary, forwards=forwards, backwards=backwards, tol=tol)

    log.debug(f'Fit power: model before fixing {model}')
    if model.wind_speed < 0:
        model = model._replace(wind_speed=abs(model.wind_speed), wind_heading=model.wind_heading+180)
    model = model._replace(wind_heading=model.wind_heading % 360)

    log.debug(f'Fit power: final model {model}')
    return model


if __name__ == '__main__':
    s = session('-v 5')
    route = activity_statistics(s, Names.LATITUDE, Names.LONGITUDE, Names.SPHERICAL_MERCATOR_X,
                                Names.SPHERICAL_MERCATOR_Y, Names.DISTANCE, Names.ELEVATION, Names.SPEED,
                                Names.CADENCE, bookmarks=bookmarks(s, '60/20/0'), with_timespan=True)
    route.sort_index(inplace=True)
    route = add_differentials(route)  # todo max_gap
    print(route.describe())
    print(route.loc[route[Names.DELTA_DISTANCE] > 1000])
