
from collections import namedtuple
from logging import getLogger

# hide from imports of this package
import numpy as _np
import scipy as _sp
from math import pi

import ch2.common.args
from .frame import median_dt
from .lib import fit, inplace_decay
from ..lib.data import tmp_name, safe_first
from ..names import Names as N

log = getLogger(__name__)
RAD_TO_DEG = 180 / pi


def add_differentials(df, max_gap=None):
    return _add_differentials(df, N.SPEED, N.DISTANCE, N.ELEVATION, N.SPEED, N.SPEED_2,
                              N.LATITUDE, N.LONGITUDE, max_gap=max_gap)


@safe_first
def add_air_speed(df, wind_speed=0, wind_heading=0, max_gap=None):
    df[N.AIR_SPEED] = df[N.SPEED] + wind_speed * _np.cos((df[N.HEADING] - wind_heading) / RAD_TO_DEG)
    return _add_differentials(df, N.AIR_SPEED, N.AIR_SPEED, max_gap=max_gap)


def _add_differentials(df, speed, *names, max_gap=None):

    # rather than use timespans (old approach) it's more reliable to discard any intervals
    # over a certain time gap.

    speed_2 = N._sqr(speed)
    df[speed_2] = df[speed] ** 2

    tmp = tmp_name()
    df[tmp] = df.index
    df[tmp] = df[tmp].diff().dt.seconds

    for name in names:
        df[N._delta(name)] = df[name].diff()
        df.loc[df[tmp] > max_gap, [N._delta(name)]] = _np.nan

    if N.LATITUDE in names and N.LONGITUDE in names and N.HEADING not in df.columns and \
            not df[N._delta(N.LONGITUDE)].dropna().empty and not df[N._delta(N.LATITUDE)].dropna().empty:
        df[N.HEADING] = _np.arctan2(df[N._delta(N.LONGITUDE)], df[N._delta(N.LATITUDE)]) * RAD_TO_DEG
        df.loc[df[tmp] > max_gap, [N.HEADING]] = _np.nan

    avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(df[speed], df[speed][1:])]
    df[N._avg(speed_2)] = [_np.nan] + avg_speed_2
    if max_gap:
        df.loc[df[tmp] > max_gap, [N._avg(speed_2)]] = _np.nan

    df.drop(columns=[tmp], inplace=True)
    return df


@safe_first
def add_energy_budget(df, m, g=9.8):
    # if DELTA_ELEVATION is +ve we've gone uphill.  so this is the total amount of energy
    # gained in this segment.
    df[N.DELTA_ENERGY] = m * (df[N.DELTA_SPEED_2] / 2 + df[N.DELTA_ELEVATION] * g)
    return df


def add_cda_estimate(df, p=1.225):
    # https://www.cyclingpowerlab.com/CyclingAerodynamics.aspx
    # assume that all energy lost (-ve gain) is due to air resistance.
    df[N.CDA] = -df[N.DELTA_ENERGY] / (p * df[N.AVG_AIR_SPEED_2] * df[N.DELTA_DISTANCE] * 0.5)
    return df


def add_crr_estimate(df, m, g=9.8):
    # assume that all energy lost is due to rolling resistance
    df[N.CRR] = -df[N.DELTA_ENERGY] / (df[N.DELTA_DISTANCE] * m * g)
    return df


@safe_first
def add_loss_estimate(df, m, cda=0.45, crr=0, p=1.225, g=9.8):
    # this is the energy spent on air and rolling resistance
    df[N.LOSS] = (cda * p * df[N.AVG_AIR_SPEED_2] * 0.5 + crr * m * g) * df[N.DELTA_DISTANCE]
    return df


@safe_first
def add_power_estimate(df):
    # power input must balance the energy budget.
    df[N.POWER_ESTIMATE] = (df[N.DELTA_ENERGY] + df[N.LOSS]) / df[N.DELTA_TIME].dt.total_seconds()
    df[N.POWER_ESTIMATE].clip(lower=0, inplace=True)
    if N.CADENCE in df.columns: df.loc[df[N.CADENCE] < 1, [N.POWER_ESTIMATE]] = 0
    df.loc[df[N.POWER_ESTIMATE].isna(), [N.POWER_ESTIMATE]] = 0
    energy = (df[N.POWER_ESTIMATE].iloc[1:] * df[N.DELTA_TIME].iloc[1:]).cumsum()
    df[N.ENERGY] = 0
    df.loc[1:, [N.ENERGY]] = energy
    return df


def add_modeled_hr(df, window, slope, delay):
    dt = median_dt(df)
    window, delay = int(0.5 + window / dt), delay / dt
    df[N.DETRENDED_HEART_RATE] = df[N.HEART_RATE] - df[N.HEART_RATE].rolling(window, center=True, min_periods=1).median()
    df[N.PREDICTED_HEART_RATE] = df[N.POWER_ESTIMATE] * slope
    inplace_decay(df, N.PREDICTED_HEART_RATE, delay)
    df[N.PREDICTED_HEART_RATE] -= df[N.PREDICTED_HEART_RATE].rolling(window, center=True, min_periods=1).median()
    return df


def measure_initial_delay(df, dt=None, col1=N.HEART_RATE, col2=N.POWER_ESTIMATE, n=20):
    dt = dt or median_dt(df)
    correln = [(i, df[col1].corr(df[col2].shift(freq=f'{i * dt}S'))) for i in range(-n, n + 1)]
    correln = sorted(correln, key=lambda c: c[1], reverse=True)
    return dt * correln[0][0]


def measure_initial_scaling(df):
    delay = measure_initial_delay(df)
    if delay < 0: raise PowerException('Cannot estimate delay (insufficient data?)')
    df[N.DELAYED_POWER] = df[N.POWER_ESTIMATE].shift(freq=f'{delay}S')
    clean = df.loc[:, (N.DELAYED_POWER, N.HEART_RATE)].dropna()
    fit = _sp.stats.linregress(x=clean[N.DELAYED_POWER], y=clean[N.HEART_RATE])
    log.debug(f'Initial fit {fit}')
    return fit.slope, fit.intercept,  delay


class PowerException(Exception): pass


# the 13.5 delay is from fitting my rides til 2019
# it seems oddly low to me - i wonder if i have an error confusing bins and time
PowerModel = namedtuple('PowerModel', 'cda, crr, slope, window, delay, m,  wind_speed, wind_heading',
                        defaults=[0.5, 0,   200,   60*60,  13.5,  70, 0,          0])


def evaluate(df, model, quiet=True):
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, ch2.common.args.m)
    df = add_air_speed(df, model.wind_speed, model.wind_heading)
    df = add_loss_estimate(df, ch2.common.args.m, cda=model.cda, crr=model.crr)
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

    model = fit(N.DETRENDED_HEART_RATE, N.PREDICTED_HEART_RATE, df, model, evaluate_and_extend,
                *vary, forwards=forwards, backwards=backwards, tol=tol)

    log.debug(f'Fit power: model before fixing {model}')
    if model.wind_speed < 0:
        model = model._replace(wind_speed=abs(model.wind_speed), wind_heading=model.wind_heading+180)
    model = model._replace(wind_heading=model.wind_heading % 360)

    log.debug(f'Fit power: final model {model}')
    return model
