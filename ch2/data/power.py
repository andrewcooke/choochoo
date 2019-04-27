
from collections import namedtuple
from logging import getLogger
from math import pi

import numpy as np
import pandas as pd
import scipy as sp

from ch2.data.frame import median_dt
from .lib import fit, inplace_decay
from ..stoats.names import *
from ..stoats.names import _d, _sqr, _avg

log = getLogger(__name__)
RAD_TO_DEG = 180 / pi


def add_differentials(df):
    return _add_differentials(df, SPEED, DISTANCE, ELEVATION, SPEED, SPEED_2, LATITUDE, LONGITUDE)


def add_air_speed(df, wind_speed=0, wind_heading=0):
    df[AIR_SPEED] = df[SPEED] + wind_speed * np.cos((df[HEADING] - wind_heading) / RAD_TO_DEG)
    return _add_differentials(df, AIR_SPEED)


def _add_differentials(df, speed, *names):

    speed_2 = _sqr(speed)
    df[speed_2] = df[speed] ** 2

    def diff():
        for _, old_span in df.groupby(TIMESPAN_ID):
            # discard leading and trailing na
            subset = old_span[list(names)].isna().any(axis=1).replace(True, np.nan)
            start, finish = subset.first_valid_index(), subset.last_valid_index()
            if start and finish:
                old_span = old_span.loc[start:finish]

                if all(len(old_span[name]) == len(old_span[name].dropna()) for name in names):
                    new_span = pd.DataFrame(index=old_span.index)
                    for col in names:
                        new_span[_d(col)] = old_span[col].diff()
                    if HEADING not in old_span.columns:
                        new_span[HEADING] = np.arctan2(new_span[_d(LONGITUDE)], new_span[_d(LATITUDE)]) * RAD_TO_DEG
                    avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(old_span[speed], old_span[speed][1:])]
                    new_span[_avg(speed_2)] = [np.nan] + avg_speed_2
                    yield new_span

    spans = list(diff())
    if len(spans):
        extra = pd.concat(spans)
        return df.drop(columns=list(extra.columns), errors='ignore').join(extra)
    else:
        raise PowerException('Missing data - found no spans without NANs')


def add_energy_budget(df, m, g=9.8):
    # if DELTA_ELEVATION is +ve we've gone uphill.  so this is the total amount of energy
    # gained in this segment.
    df[DELTA_ENERGY] = m * (df[DELTA_SPEED_2] / 2 + df[DELTA_ELEVATION] * g)
    return df


def add_cda_estimate(df, p=1.225):
    # https://www.cyclingpowerlab.com/CyclingAerodynamics.aspx
    # assume that all energy lost (-ve gain) is due to air resistance.
    df[CDA] = -df[DELTA_ENERGY] / (p * df[AVG_AIR_SPEED_2] * df[DELTA_DISTANCE] * 0.5)
    return df


def add_crr_estimate(df):
    # assume that all energy lost is due to rolling resistance
    df[CRR] = -df[DELTA_ENERGY] / df[DELTA_DISTANCE]
    return df


def add_loss_estimate(df, cda=0.45, crr=0, p=1.225):
    # this is the energy spent on air and rolling resistance
    df[LOSS] = (cda * p * df[AVG_AIR_SPEED_2] * 0.5 + crr) * df[DELTA_DISTANCE]
    return df


def add_power_estimate(df):
    # power input must balance the energy budget.
    df[POWER_ESTIMATE] = (df[DELTA_ENERGY] + df[LOSS]) / df[DELTA_TIME].dt.total_seconds()
    df[POWER_ESTIMATE].clip(lower=0, inplace=True)
    if CADENCE in df.columns: df.loc[df[CADENCE] < 1, [POWER_ESTIMATE]] = 0
    df.loc[df[POWER_ESTIMATE].isna(), [POWER_ESTIMATE]] = 0
    energy = (df[POWER_ESTIMATE].iloc[1:] * df[DELTA_TIME].iloc[1:]).cumsum()
    df[ENERGY] = 0
    df.loc[1:, [ENERGY]] = energy
    return df


def add_modeled_hr(df, window, slope, delay):
    dt = median_dt(df)
    window, delay = int(0.5 + window / dt), delay / dt
    df[DETRENDED_HEART_RATE] = df[HEART_RATE] - df[HEART_RATE].rolling(window, center=True, min_periods=1).median()
    df[PREDICTED_HEART_RATE] = df[POWER_ESTIMATE] * slope
    inplace_decay(df, PREDICTED_HEART_RATE, delay)
    df[PREDICTED_HEART_RATE] -= df[PREDICTED_HEART_RATE].rolling(window, center=True, min_periods=1).median()
    return df


def measure_initial_delay(df, dt=None, col1=HEART_RATE, col2=POWER_ESTIMATE, n=20):
    dt = dt or median_dt(df)
    correln = [(i, df[col1].corr(df[col2].shift(freq=f'{i * dt}S'))) for i in range(-n, n + 1)]
    correln = sorted(correln, key=lambda c: c[1], reverse=True)
    return dt * correln[0][0]


def measure_initial_scaling(df):
    delay = measure_initial_delay(df)
    if delay < 0: raise PowerException('Cannot estimate delay (insufficient data?)')
    df[DELAYED_POWER] = df[POWER_ESTIMATE].shift(freq=f'{delay}S')
    clean = df.loc[:, (DELAYED_POWER, HEART_RATE)].dropna()
    fit = sp.stats.linregress(x=clean[DELAYED_POWER], y=clean[HEART_RATE])
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
    df = add_loss_estimate(df, model.cda, model.crr)
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

    model = fit(DETRENDED_HEART_RATE, PREDICTED_HEART_RATE, df, model, evaluate_and_extend,
                *vary, forwards=forwards, backwards=backwards, tol=tol)

    log.debug(f'Fit power: model before fixing {model}')
    if model.wind_speed < 0:
        model = model._replace(wind_speed=abs(model.wind_speed), wind_heading=model.wind_heading+180)
    model = model._replace(wind_heading=model.wind_heading % 360)

    log.debug(f'Fit power: final model {model}')
    return model
