
from collections import namedtuple
from json import loads
from math import pi

import numpy as np
import pandas as pd
import scipy as sp

from . import DataFrameStatistics
from .mproc.pipeline import DataFrameCalculator, ActivityJournalCalculator
from ..load import StatisticJournalLoader
from ..names import *
from ..names import _sqr, _d, _avg
from ...data import activity_statistics
from ...data.power import median_freq, linear_resample
from ...lib.data import reftuple, MissingReference
from ...squeal import StatisticJournalFloat, Constant


Power = reftuple('Power', 'bike, weight, p, g', defaults=(70, 1.225, 9.8))
Bike = namedtuple('Bike', 'cda, crr, m')

RAD_TO_DEG = 180 / pi


# used as common owner
class PowerStatistics(DataFrameStatistics):

    def __init__(self, log, *args, **kargs):
        super().__init__(log, *args, **kargs)
        self.owner = PowerStatistics  # fixed for subclasses
        self.power = None


class PowerCalculator(ActivityJournalCalculator):

    def __init__(self, log, *args, **kargs):
        super().__init__(log, *args, owner_out=PowerCalculator, **kargs)
        self.power = None


class PowerException(Exception): pass


class BasicPowerStatistics(PowerStatistics):

    def _set_power(self, s, ajournal, df):
        power_ref = self._karg('power')
        power = Power(**loads(Constant.get(s, power_ref).at(s).value))
        # default owner is constant since that's what users can tweak
        self.power = power.expand(self._log, s, df[TIME].iloc[0], owner=Constant, constraint=ajournal.activity_group)
        self._log.debug(f'{power_ref}: {self.power}')

    def _load_data(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, CADENCE, LATITUDE, LONGITUDE, HEART_RATE,
                                     activity_journal_id=ajournal.id, with_timespan=True,
                                     log=self._log, quiet=True)
            _, df = linear_resample(df)
            df = add_differentials(df)
            self._set_power(s, ajournal, df)
            return df
        except PowerException as e:
            self._log.warn(e)
        except MissingReference as e:
            self._log.warning(f'Power configuration incorrect ({e})')
        except Exception as e:
            self._log.warning(f'Failed to generate statistics for power: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        df = add_energy_budget(df, self.power.bike['m'] + self.power.weight, self.power.g)
        df = add_loss_estimate(df, self.power.bike['cda'], self.power.bike['crr'], self.power.p)
        df = add_power_estimate(df)
        return df

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            for name, units, summary in [(POWER, W, AVG), (HEADING, DEG, None)]:
                if not pd.isnull(row[name]):
                    loader.add(name, units, summary, ajournal.activity_group, ajournal, row[name], time,
                               StatisticJournalFloat)


class BasicPowerCalculator(PowerCalculator):

    def __init__(self, *args, **kargs):
        # a lot of reading for not much writing
        super().__init__(*args, cost_calc=10, cost_write=1, **kargs)

    def _set_power(self, s, ajournal, df):
        power_ref = self._karg('power')
        power = Power(**loads(Constant.get(s, power_ref).at(s).value))
        # default owner is constant since that's what users can tweak
        self.power = power.expand(self._log, s, df[TIME].iloc[0], owner=Constant, constraint=ajournal.activity_group)
        self._log.debug(f'{power_ref}: {self.power}')

    def _load_data(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, CADENCE, LATITUDE, LONGITUDE, HEART_RATE,
                                     activity_journal_id=ajournal.id, with_timespan=True,
                                     log=self._log, quiet=True)
            _, df = linear_resample(df)
            df = add_differentials(df)
            self._set_power(s, ajournal, df)
            return df
        except PowerException as e:
            self._log.warn(e)
        except MissingReference as e:
            self._log.warning(f'Power configuration incorrect ({e})')
        except Exception as e:
            self._log.warning(f'Failed to generate statistics for power: {e}')
            raise

    def _calculate_stats(self, s, ajournal, data):
        data = add_energy_budget(data, self.power.bike['m'] + self.power.weight, self.power.g)
        data = add_loss_estimate(data, self.power.bike['cda'], self.power.bike['crr'], self.power.p)
        data = add_power_estimate(data)
        return data

    def _copy_results(self, s, ajournal, loader, data):
        for time, row in data.iterrows():
            for name, units, summary in [(POWER, W, AVG), (HEADING, DEG, None)]:
                if not pd.isnull(row[name]):
                    loader.add(name, units, summary, ajournal.activity_group, ajournal, row[name], time,
                               StatisticJournalFloat)


class ExtendedPowerStatistics(BasicPowerStatistics):

    def _add_stats(self, s, ajournal):
        df = self._load_data(s, ajournal)
        if df is not None and len(df):
            try:
                stats = self._calculate_stats(s, ajournal, df)
                loader = StatisticJournalLoader(self._log, s, self.owner)
                self._copy_results(s, ajournal, loader, stats)
                loader.load()
            except PowerException as e:
                self._log.warning(f'Cannot model power; adding basic values only ({e})')
                stats = super()._calculate_stats(s, ajournal, df)
                loader = StatisticJournalLoader(self._log, s, self.owner)
                super()._copy_results(s, ajournal, loader, stats)
                loader.load()
        else:
            self._log.warning('No statistics for %s' % ajournal)

    def _calculate_stats(self, s, ajournal, df):
        model = fit_power(self._log, df, 'slope', 'intercept', 'adaption', 'delay',
                          cda=self.power.bike['cda'], crr=self.power.bike['crr'],
                          m=self.power.bike['m'] + self.power.weight, g=self.power.g, p=self.power.p)
        df = evaluate(self._log, df, model, quiet=False)
        return model, df

    def _copy_results(self, s, ajournal, loader, results):
        model, df = results
        # how much energy every heart beat
        # 60W at 60bpm is 60J every second or beat; 60W at 1bpm is 3600J every minute or beat;
        # 1W at 1bpm is 60J every minute or beat
        # slope is BPM / W; 1/slope is W/BPM = W/PM = WM = 60Ws
        loader.add(POWER_HR, J, AVG, ajournal.activity_group, ajournal, 60 / model.slope, ajournal.start,
                   StatisticJournalFloat)
        loader.add(LOG_HR_DRIFT, None, AVG, ajournal.activity_group, ajournal, model.adaption, ajournal.start,
                   StatisticJournalFloat)
        loader.add(IDLE_HR, BPM, AVG, ajournal.activity_group, ajournal, model.intercept, ajournal.start,
                   StatisticJournalFloat)
        # has to come after the above to get times in order
        super()._copy_results(s, ajournal, loader, df)


def add_differentials(df):
    return _add_differentials(df, SPEED, DISTANCE, ELEVATION, SPEED, SPEED_2, LATITUDE, LONGITUDE)


def add_air_speed(df, speed=0, heading=0):
    df[AIR_SPEED] = df[SPEED] + speed * np.cos(df[HEADING] / RAD_TO_DEG - heading + pi / 2)
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
        raise PowerException('Missing data')


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
    df[LOSS] = (cda * p * df[AVG_SPEED_2] * 0.5 + crr) * df[DELTA_DISTANCE]
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


def measure_initial_delay(df, freq=None, col1=HEART_RATE, col2=POWER, n=20):
    freq = freq or median_freq(df)
    correln = [(i, df[col1].corr(df[col2].shift(freq=i * freq))) for i in range(-n, n+1)]
    correln = sorted(correln, key=lambda c: c[1], reverse=True)
    return freq, correln[0][0]


def measure_initial_scaling(log, df):
    freq, delay = measure_initial_delay(df)
    if delay < 0: raise PowerException('Cannot estimate delay (insufficient data?)')
    hr_smoothed = df[HEART_RATE].rolling(10, center=True).median().dropna()
    h0, h1 = hr_smoothed.iloc[0], hr_smoothed.iloc[-1]
    e0, e1 = df[ENERGY].iloc[0], df[ENERGY].iloc[-1]
    adaption = (h1 - h0) / (e1 - e0)
    xy = (df[HEART_RATE] - adaption * df[ENERGY]).rename(COR_HEART_RATE).to_frame().join(
        df[POWER].shift(freq=delay*freq).to_frame(),
        how='inner')
    fit = sp.stats.linregress(x=xy[POWER], y=xy[COR_HEART_RATE])
    log.debug(f'Initial fit {fit}')
    return fit.slope, fit.intercept, adaption, delay


Model = namedtuple('Model', 'cda, crr, slope, intercept, adaption, delay, m,   g,   p,     speed, heading',
                   defaults=[0,   0,   0,     0,         0,        6,     70,  9.8, 1.225, 0,     0])


def evaluate(log, df, model, quiet=True):
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, model.m, model.g)
    df = add_air_speed(df, model.speed, model.heading)
    df = add_loss_estimate(df, model.cda, model.crr, model.p)
    return add_power_estimate(df)


MIN_DELAY = 1


def fix_delay(model):
    return MIN_DELAY + abs(model.delay - MIN_DELAY)


def chisq(log, df, model):
    df = evaluate(log, df, model)
    pred = (df[POWER] * model.slope + model.intercept).ewm(halflife=fix_delay(model)).mean()
    obs = df[HEART_RATE] - model.adaption * df[ENERGY]
    return sp.stats.chisquare(pred, obs).statistic


def fit_power(log, df, *vary, **initial):

    model = Model()._replace(**initial)
    df = evaluate(log, df, model)
    slope, intercept, adaption, delay = measure_initial_scaling(log, df)
    model = model._replace(slope=slope, intercept=intercept, adaption=adaption, delay=delay)

    def local_chisq(args):
        return chisq(log, df, model._replace(**dict(zip(vary, args))))

    result = sp.optimize.minimize(local_chisq, [getattr(model, name) for name in vary],
                                  method='Nelder-Mead', tol=0.01, options={'disp': True})

    model = model._replace(**dict(zip(vary, result.x)))
    model = model._replace(delay=fix_delay(model))
    return model
