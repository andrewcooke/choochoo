from collections import namedtuple
from logging import getLogger
from math import pi, log10

import numpy as np
import pandas as pd
import scipy as sp

from ch2.data.fit import fit
from ..stoats.names import *
from ..stoats.names import _d, _sqr, _avg

log = getLogger(__name__)
RAD_TO_DEG = 180 / pi


def median_dt(stats):
    return pd.Series(stats.index).diff().median().total_seconds()


def linear_resample(stats, start=None, finish=None, dt=None, with_timestamp=None, keep_nan=True):
    if with_timestamp is None: with_timestamp = TIMESPAN_ID in stats.columns
    dt = dt or median_dt(stats)
    start = start or stats.index.min()
    finish = finish or stats.index.max()
    even = pd.DataFrame({'keep': True}, index=pd.date_range(start=start, end=finish, freq=f'{dt}S'))
    both = stats.join(even, how='outer', sort=True)
    both.loc[both['keep'] != True, ['keep']] = False  # not sure this is needed, but avoid interpolating to true
    both.interpolate(method='index', limit_area='inside', inplace=True)
    resampled = both.loc[both['keep'] == True].drop(columns=['keep'])
    resampled[TIME] = resampled.index
    resampled[DELTA_TIME] = resampled[TIME].diff()
    if with_timestamp:
        if keep_nan:
            resampled.loc[~resampled[TIMESPAN_ID].isin(stats[TIMESPAN_ID].unique())] = np.nan
        else:
            resampled = resampled.loc[resampled[TIMESPAN_ID].isin(stats[TIMESPAN_ID].unique())]
    return resampled


def add_differentials(df):
    return _add_differentials(df, SPEED, DISTANCE, ELEVATION, SPEED, SPEED_2, LATITUDE, LONGITUDE)


def add_air_speed(df, wind_speed=0, wind_heading=0):
    df[AIR_SPEED] = df[SPEED] + wind_speed * np.cos((df[HEADING] - wind_heading) / RAD_TO_DEG)
    return _add_differentials(df, AIR_SPEED)


def _add_differentials(df, speed, *names):

    speed_2 = _sqr(speed)
    df[speed_2] = df[speed] ** 2

    def diff():
        for _, span in df.groupby(TIMESPAN_ID):
            if all(len(span[name]) == len(span[name].dropna()) for name in names):
                span = span.copy()
                for col in names:
                    span[_d(col)] = span[col].diff()
                if HEADING not in span.columns:
                    span[HEADING] = np.arctan2(span[_d(LONGITUDE)], span[_d(LATITUDE)]) * RAD_TO_DEG
                avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(span[speed], span[speed][1:])]
                span[_avg(speed_2)] = [np.nan] + avg_speed_2
                yield span

    spans = list(diff())
    if len(spans):
        return pd.concat(spans)
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
    df[POWER] = (df[DELTA_ENERGY] + df[LOSS]) / df[DELTA_TIME].dt.total_seconds()
    df[POWER].clip(lower=0, inplace=True)
    if CADENCE in df.columns: df.loc[df[CADENCE] < 1, [POWER]] = 0
    df.loc[df[POWER].isna(), [POWER]] = 0
    energy = (df[POWER].iloc[1:] * df[DELTA_TIME].iloc[1:]).cumsum()
    df[ENERGY] = 0
    df.loc[1:, [ENERGY]] = energy
    return df


def add_modeled_hr(df, log_adaption, slope, intercept, delay):
    df[DETRENDED_HEART_RATE] = df[HEART_RATE] - 10 ** log_adaption * df[ENERGY]
    df[PREDICTED_HEART_RATE] = (df[POWER] * slope + intercept).ewm(halflife=delay).mean()
    return df


def measure_initial_delay(df, dt=None, col1=HEART_RATE, col2=POWER, n=20):
    dt = dt or median_dt(df)
    correln = [(i, df[col1].corr(df[col2].shift(freq=f'{i * dt}S'))) for i in range(-n, n + 1)]
    correln = sorted(correln, key=lambda c: c[1], reverse=True)
    return dt * correln[0][0]


def measure_initial_scaling(df):
    delay = measure_initial_delay(df)
    if delay < 0: raise PowerException('Cannot estimate delay (insufficient data?)')
    hr_smoothed = df[HEART_RATE].rolling(10, center=True).median().dropna()
    h0, h1 = hr_smoothed.iloc[0], hr_smoothed.iloc[-1]
    e0, e1 = df[ENERGY].iloc[0], df[ENERGY].iloc[-1]
    adaption = (h1 - h0) / (e1 - e0)
    log_adaption = log10(adaption) if adaption > 0 else -99
    xy = (df[HEART_RATE] - 10 ** log_adaption * df[ENERGY]).rename(COR_HEART_RATE).to_frame().join(
        df[POWER].shift(freq=f'{delay}S').to_frame(),
        how='inner')
    fit = sp.stats.linregress(x=xy[POWER], y=xy[COR_HEART_RATE])
    log.debug(f'Initial fit {fit}')
    return log_adaption, fit.slope, fit.intercept,  delay


class PowerException(Exception): pass


PowerModel = namedtuple('PowerModel', 'cda, crr, slope, intercept, log_adaption, delay, m,  wind_speed, wind_heading',
                             defaults=[0,   0,   0,     0,         0,            40,    70, 0,          0])


def evaluate(df, model, quiet=True):
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, model.m)
    df = add_air_speed(df, model.wind_speed, model.wind_heading)
    df = add_loss_estimate(df, model.cda, model.crr)
    df = add_power_estimate(df)
    df = add_modeled_hr(df, model.log_adaption, model.slope, model.intercept, model.delay)
    return df


MIN_DELAY = 1


def fit_power(df, model, *vary):

    log.debug(f'Fit power: varying {vary}')
    df = evaluate(df, model)
    log_adaption, slope, intercept, delay = measure_initial_scaling(df)
    model = model._replace(log_adaption=log_adaption, slope=slope, intercept=intercept, delay=delay)
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
        df[DETRENDED_HEART_RATE] = df[HEART_RATE] - 10 ** model.log_adaption * df[ENERGY]
        df[PREDICTED_HEART_RATE] = (df[POWER] * model.slope + model.intercept).ewm(halflife=model.delay).mean()
        return df

    model = fit(DETRENDED_HEART_RATE, PREDICTED_HEART_RATE, df, model, evaluate_and_extend,
                *vary, forwards=forwards, backwards=backwards)

    log.debug(f'Fit power: model before fixing {model}')
    if model.wind_speed < 0:
        model = model._replace(wind_speed=abs(model.wind_speed), wind_heading=model.wind_heading+180)
    model = model._replace(wind_heading=model.wind_heading % 360)

    log.debug(f'Fit power: final model {model}')
    return model
