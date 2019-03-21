
from collections import namedtuple
from json import loads
from logging import getLogger

import pandas as pd

from . import DataFrameCalculatorMixin, ActivityJournalCalculatorMixin, MultiProcCalculator
from ..load import StatisticJournalLoader
from ..names import *
from ...data import activity_statistics
from ...data.power import linear_resample, add_differentials, add_energy_budget, add_loss_estimate, \
    add_power_estimate, PowerException, evaluate, fit_power, PowerModel, add_air_speed, add_modeled_hr, median_dt
from ...lib.data import reftuple, MissingReference
from ...lib.log import log_current_exception
from ...squeal import StatisticJournalFloat, Constant, Timestamp

log = getLogger(__name__)
# these configure the model.
# todo - add varying and stuff we want to fix (w defaults)
Power = reftuple('Power', 'bike, rider_weight', defaults=(70,))
Bike = namedtuple('Bike', 'cda, crr, weight')


# used as common owner
class PowerCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, **kargs):
        super().__init__(*args, owner_out=PowerCalculator, **kargs)
        self.power = None


class BasicPowerCalculator(PowerCalculator):

    # a lot of reading for not much writing
    def __init__(self, *args, cost_calc=10, cost_write=1, power=None, **kargs):
        self.power_ref = power
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _set_power(self, s, ajournal, df):
        power = Power(**loads(Constant.get(s, self.power_ref).at(s).value))
        # default owner is constant since that's what users can tweak
        self.power = power.expand(log, s, ajournal.start, owner=Constant, constraint=ajournal.activity_group)
        log.debug(f'Power: {self.power_ref}: {self.power}')

    def _read_dataframe(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, CADENCE, LATITUDE, LONGITUDE, HEART_RATE,
                                     activity_journal_id=ajournal.id, with_timespan=True,
                                     quiet=True)
            df = linear_resample(df)
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

    def _calculate_stats(self, s, ajournal, df):
        df = add_energy_budget(df, self.power.bike['weight'] + self.power.weight)
        df = add_air_speed(df, 0, 0)
        df = add_loss_estimate(df, self.power.bike['cda'], self.power.bike['crr'])
        df = add_power_estimate(df)
        return df

    def _copy_results(self, s, ajournal, loader, df,
                      fields=((POWER, W, AVG), (HEADING, DEG, None))):
        for time, row in df.iterrows():
            for name, units, summary in fields:
                if not pd.isnull(row[name]):
                    loader.add(name, units, summary, ajournal.activity_group, ajournal, row[name], time,
                               StatisticJournalFloat)


class ExtendedPowerCalculator(BasicPowerCalculator):

    # lots of fitting
    def __init__(self, *args, cost_calc=100, cost_write=1, **kargs):
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _run_one(self, s, time_or_date):
        source = self._get_source(s, time_or_date)
        s.commit()  # free up database
        with Timestamp(owner=self.owner_out, key=source.id).on_success(log, s):
            try:
                data = self._read_dataframe(s, source)
                loader = StatisticJournalLoader(s, self.owner_out)
                try:
                    stats = self._calculate_stats(s, source, data)
                except PowerException as e:
                    log.warning(f'Cannot model power; adding basic values only ({e})')
                    loader = StatisticJournalLoader(s, self.owner_out)
                    stats = None, None, super()._calculate_stats(s, source, data)
                self._copy_results(s, source, loader, stats)
                loader.load()
            except Exception as e:
                log.warning(f'No statistics on {time_or_date}')
                log_current_exception()

    def _calculate_stats(self, s, ajournal, df):
        model = PowerModel(cda=self.power.bike['cda'], crr=self.power.bike['crr'],
                           m=self.power.bike['weight'] + self.power.rider_weight,
                           wind_speed=10, wind_heading=180)  # todo - ranges?
        for name in self.power._fields:
            if name in model._fields:
                setattr(model, name, getattr(self.power, name))
        model = fit_power(df, model, 'slope', 'intercept', 'delay', 'wind_speed', 'wind_heading')
        df = evaluate(df, model, quiet=False)
        df = add_modeled_hr(df, int(0.5 + model.window / median_dt(df)), model.slope, model.intercept, model.delay)
        return model, df

    def _copy_results(self, s, ajournal, loader, stats):
        model, df = stats
        if model:
            # how much energy every heart beat
            # 60W at 60bpm is 60J every second or beat; 60W at 1bpm is 3600J every minute or beat;
            # 1W at 1bpm is 60J every minute or beat
            # slope is BPM / W; 1/slope is W/BPM = W/PM = WM = 60Ws
            loader.add(POWER_HR, J, AVG, ajournal.activity_group, ajournal, 60 / model.slope, ajournal.start,
                       StatisticJournalFloat)
            # todo units - bpm/J?
            loader.add(IDLE_HR, BPM, AVG, ajournal.activity_group, ajournal, model.intercept, ajournal.start,
                       StatisticJournalFloat)
            loader.add(POWER_HR_LAG, S, AVG, ajournal.activity_group, ajournal, model.delay,
                       ajournal.start, StatisticJournalFloat)
            loader.add(WIND_SPEED, MS, AVG, ajournal.activity_group, ajournal, model.wind_speed,
                       ajournal.start, StatisticJournalFloat)
            loader.add(WIND_HEADING, DEG, AVG, ajournal.activity_group, ajournal, model.wind_heading,
                       ajournal.start, StatisticJournalFloat)
        # has to come after the above to get times in order
        super()._copy_results(s, ajournal, loader, df,
                              fields=((POWER, W, AVG), (HEADING, DEG, None),
                                      (PREDICTED_HEART_RATE, BPM, None), (DETRENDED_HEART_RATE, BPM, None)))

