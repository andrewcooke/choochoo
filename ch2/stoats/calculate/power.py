
from collections import namedtuple
from json import loads
from logging import getLogger
from sys import exc_info
from traceback import format_tb

import pandas as pd

from .mproc.pipeline import ActivityJournalCalculator
from ..load import StatisticJournalLoader
from ..names import *
from ...data import activity_statistics
from ...data.power import linear_resample, add_differentials, add_energy_budget, add_loss_estimate, \
    add_power_estimate, PowerException, evaluate, fit_power
from ...lib.data import reftuple, MissingReference
from ...squeal import StatisticJournalFloat, Constant

log = getLogger(__name__)
Power = reftuple('Power', 'bike, weight, p, g', defaults=(70, 1.225, 9.8))
Bike = namedtuple('Bike', 'cda, crr, m')


# used as common owner
class PowerCalculator(ActivityJournalCalculator):

    def __init__(self, log, *args, **kargs):
        super().__init__(log, *args, owner_out=PowerCalculator, **kargs)
        self.power = None


class BasicPowerCalculator(PowerCalculator):

    # a lot of reading for not much writing
    def __init__(self, *args, cost_calc=10, cost_write=1, power=None, **kargs):
        self.power_ref = power
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _set_power(self, s, ajournal, df):
        power = Power(**loads(Constant.get(s, self.power_ref).at(s).value))
        # default owner is constant since that's what users can tweak
        self.power = power.expand(log, s, df[TIME].iloc[0], owner=Constant, constraint=ajournal.activity_group)
        log.debug(f'{self.power_ref}: {self.power}')

    def _load_data(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, CADENCE, LATITUDE, LONGITUDE, HEART_RATE,
                                     activity_journal_id=ajournal.id, with_timespan=True,
                                     quiet=True)
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


class ExtendedPowerCalculator(BasicPowerCalculator):

    # lots of fitting
    def __init__(self, *args, cost_calc=100, cost_write=1, **kargs):
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _run_one(self, s, time_or_date):
        try:
            source = self._get_source(s, time_or_date)
            data = self._load_data(s, source)
            loader = StatisticJournalLoader(log, s, self.owner_out)
            try:
                stats = self._calculate_stats(s, source, data)
            except PowerException as e:
                self._log.warning(f'Cannot model power; adding basic values only ({e})')
                loader = StatisticJournalLoader(log, s, self.owner_out)
                stats = None, super()._calculate_stats(s, source, data)
            self._copy_results(s, source, loader, stats)
            loader.load()
        except Exception as e:
            log.warning(f'No statistics on {time_or_date} ({e})')
            log.debug('\n' + ''.join(format_tb(exc_info()[2])))

    def _calculate_stats(self, s, ajournal, data):
         model = fit_power(data, 'slope', 'intercept', 'adaption', 'delay',
                           cda=self.power.bike['cda'], crr=self.power.bike['crr'],
                           m=self.power.bike['m'] + self.power.weight, g=self.power.g, p=self.power.p)
         data = evaluate(data, model, quiet=False)
         return model, data

    def _copy_results(self, s, ajournal, loader, stats):
        model, data = stats
        if model:
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
        super()._copy_results(s, ajournal, loader, data)

