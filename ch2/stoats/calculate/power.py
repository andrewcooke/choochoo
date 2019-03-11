
from collections import namedtuple
from json import loads
from logging import getLogger

import pandas as pd
import scipy as sp

from ch2.data.power import PowerException
from . import DataFrameStatistics
from .mproc.pipeline import ActivityJournalCalculator
from ..load import StatisticJournalLoader
from ..names import *
from ...data import activity_statistics
from ...data.power import linear_resample, add_differentials, add_air_speed, add_energy_budget, add_loss_estimate, \
    add_power_estimate, measure_initial_scaling
from ...lib.data import reftuple, MissingReference
from ...squeal import StatisticJournalFloat, Constant


log = getLogger(__name__)
Power = reftuple('Power', 'bike, weight, p, g', defaults=(70, 1.225, 9.8))
Bike = namedtuple('Bike', 'cda, crr, m')


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
        self.power = power.expand(log, s, df[TIME].iloc[0], owner=Constant, constraint=ajournal.activity_group)
        log.debug(f'{power_ref}: {self.power}')

    def _load_data(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, CADENCE, LATITUDE, LONGITUDE, HEART_RATE,
                                     activity_journal_id=ajournal.id, with_timespan=True,
                                     log=log, quiet=True)
            _, df = linear_resample(df)
            df = add_differentials(df)
            self._set_power(s, ajournal, df)
            return df
        except PowerException as e:
            log.warning(e)
        except MissingReference as e:
            log.warning(f'Power configuration incorrect ({e})')
        except Exception as e:
            log.warning(f'Failed to generate statistics for power: {e}')
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
        model = fit_power(df, 'slope', 'intercept', 'adaption', 'delay',
                          cda=self.power.bike['cda'], crr=self.power.bike['crr'],
                          m=self.power.bike['m'] + self.power.weight, g=self.power.g, p=self.power.p)
        df = evaluate(df, model, quiet=False)
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


Model = namedtuple('Model', 'cda, crr, slope, intercept, adaption, delay, m,   g,   p,     speed, heading',
                   defaults=[0,   0,   0,     0,         0,        6,     70,  9.8, 1.225, 0,     0])


def evaluate(df, model, quiet=True):
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, model.m, model.g)
    df = add_air_speed(df, model.speed, model.heading)
    df = add_loss_estimate(df, model.cda, model.crr, model.p)
    return add_power_estimate(df)


MIN_DELAY = 1


def fix_delay(model):
    return MIN_DELAY + abs(model.delay - MIN_DELAY)


def chisq(df, model):
    df = evaluate(df, model)
    pred = (df[POWER] * model.slope + model.intercept).ewm(halflife=fix_delay(model)).mean()
    obs = df[HEART_RATE] - model.adaption * df[ENERGY]
    return sp.stats.chisquare(pred, obs).statistic


def fit_power(df, *vary, **initial):

    model = Model()._replace(**initial)
    df = evaluate(df, model)
    slope, intercept, adaption, delay = measure_initial_scaling(df)
    model = model._replace(slope=slope, intercept=intercept, adaption=adaption, delay=delay)

    def local_chisq(args):
        return chisq(df, model._replace(**dict(zip(vary, args))))

    result = sp.optimize.minimize(local_chisq, [getattr(model, name) for name in vary],
                                  method='Nelder-Mead', tol=0.01, options={'disp': True})

    model = model._replace(**dict(zip(vary, result.x)))
    model = model._replace(delay=fix_delay(model))
    return model
