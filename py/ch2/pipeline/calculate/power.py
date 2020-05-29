
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np
import pandas as pd

from .utils import ActivityGroupCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator
from ...data import present, linear_resample_time, Statistics
from ...data.frame import median_dt
from ...data.lib import interpolate_to_index
from ...data.power import add_differentials, add_energy_budget, add_loss_estimate, add_power_estimate, PowerException, \
    add_air_speed
from ...lib import log_current_exception
from ...lib.data import reftuple, MissingReference
from ...names import N, Units, Summaries, T
from ...sql import StatisticJournalFloat, Constant
from ...sql.types import simple_name

log = getLogger(__name__)

BikeModel = namedtuple('BikeModel', 'cda, crr, bike_weight')


class PowerModel(reftuple('Power', 'bike_model, rider_weight')):

    def expand(self, s, time, default_owner=None, default_activity_group=None):
        super().expand(s, time, default_owner=default_owner, default_activity_group=default_activity_group)
        bike_model = self.bike_model
        if not isinstance(bike_model, BikeModel):
            self.bike_model = BikeModel(**bike_model)
        return self


class PowerCalculator(ActivityGroupCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    '''
    See ch2.config.power for examples of how this is configured.
    '''

    def __init__(self, *args, power_model=None, caloric_eff=0.25, **kargs):
        self.power_model_ref = power_model
        self.caloric_eff = caloric_eff
        super().__init__(*args, **kargs)

    def _set_power(self, s, ajournal):
        power_model = PowerModel(**loads(Constant.from_name(s, self.power_model_ref).at(s).value))
        self.power_model = power_model.expand(s, ajournal.start, default_owner=Constant)
        log.debug(f'Power: {self.power_model_ref}: {self.power_model}')

    def _read_dataframe(self, s, ajournal):
        from ..owners import SegmentReader, ElevationCalculator
        try:
            self._set_power(s, ajournal)
            df = Statistics(s, activity_journal=ajournal, with_timespan=True). \
                by_name(SegmentReader, N.DISTANCE, N.SPEED, N.CADENCE, N.LATITUDE,
                        N.LONGITUDE, N.HEART_RATE). \
                by_name(ElevationCalculator, N.ELEVATION).df
            ldf = linear_resample_time(df)
            ldf = add_differentials(ldf, max_gap=1.1 * median_dt(df))
            if N.HEADING not in ldf.columns:
                raise PowerException('Could not calculate heading')    
            return df, ldf
        except PowerException as e:
            log.warning(e)
        except MissingReference as e:
            log.warning(f'Power configuration incorrect ({e})')
        except Exception as e:
            log.warning(f'Failed to generate statistics for power ({ajournal.activity_group.name}): {e}')
            log_current_exception(traceback=True)

    def _calculate_stats(self, s, ajournal, dfs):
        df, ldf = dfs
        total_weight = self.power_model.bike_model.bike_weight + self.power_model.rider_weight
        ldf = add_energy_budget(ldf, total_weight)
        ldf = add_air_speed(ldf, 0, 0)
        ldf = add_loss_estimate(ldf, total_weight, cda=self.power_model.bike_model.cda,
                                crr=self.power_model.bike_model.crr)
        ldf = add_power_estimate(ldf)
        return df, ldf

    def _copy_results(self, s, ajournal, loader, dfs,
                      fields=((T.POWER_ESTIMATE, Units.W, Summaries.AVG, 'The estimated power.'),
                              (T.HEADING, Units.DEG, None, 'The current heading'))):
        df, ldf = dfs
        self.__add_total_energy(s, ajournal, loader, ldf)
        df = interpolate_to_index(df, ldf, *(simple_name(field[0]) for field in fields))
        for time, row in df.iterrows():
            for title, units, summary, description in fields:
                name = simple_name(title)
                if not pd.isnull(row[name]):
                    loader.add(name, units, summary, ajournal, row[name], time,
                               StatisticJournalFloat, title=title, description=description)

    def __add_total_energy(self, s, ajournal, loader, ldf):
        if present(ldf, N.POWER_ESTIMATE):
            ldf['tmp'] = ldf[N.POWER_ESTIMATE]
            ldf.loc[ldf['tmp'].isna(), ['tmp']] = 0
            energy = np.trapz(y=ldf['tmp'], x=ldf.index.astype(np.int64) / 1e12)
            loader.add(T.ENERGY_ESTIMATE, Units.KJ, Summaries.MAX, ajournal, energy, ajournal.start,
                       StatisticJournalFloat, 'The estimated total energy expended.')
            loader.add(T.CALORIE_ESTIMATE, Units.KCAL, Summaries.MAX, ajournal,
                       energy * 0.239006 / self.caloric_eff, ajournal.start, StatisticJournalFloat,
                       'The estimated calories burnt.')
            ldf.drop(columns=['tmp'], inplace=True)
