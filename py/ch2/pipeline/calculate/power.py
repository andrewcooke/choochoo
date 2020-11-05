
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np
import pandas as pd

from .utils import ActivityGroupProcessCalculator, DataFrameCalculatorMixin, ProcessCalculator
from ..pipeline import LoaderMixin
from ...common.log import log_current_exception
from ...data import present, linear_resample_time, Statistics
from ...data.frame import median_dt
from ...data.lib import interpolate_to_index
from ...data.power import add_differentials, add_energy_budget, add_loss_estimate, add_power_estimate
from ...lib.data import reftuple, MissingReference
from ...names import N, U, S, T
from ...sql import Constant, StatisticJournalType

log = getLogger(__name__)

BikeModel = namedtuple('BikeModel', 'cda, crr, bike_weight')


class PowerModel(reftuple('Power', 'bike_model, rider_weight')):

    def expand(self, s, time, default_owner=None, default_activity_group=None):
        instance = super().expand(s, time, default_owner=default_owner, default_activity_group=default_activity_group)
        bike_model = instance.bike_model
        if not isinstance(bike_model, BikeModel):
            return instance._replace(bike_model=BikeModel(**bike_model))
        else:
            return instance


class PowerCalculator(LoaderMixin, DataFrameCalculatorMixin, ActivityGroupProcessCalculator):

    def __init__(self, *args, power_model=None, caloric_eff=0.25, activity_group=None, **kargs):
        self.power_model_ref = power_model
        self.caloric_eff = caloric_eff
        super().__init__(*args, timestamp_constraint=activity_group, activity_group=activity_group, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self._provides(s, T.POWER_ESTIMATE, StatisticJournalType.FLOAT, U.W, S.AVG,
                       'The estimated power.')
        self._provides(s, T.VERTICAL_POWER, StatisticJournalType.FLOAT, U.W, S.AVG,
                       'The estimated power from height gain alone.')
        self._provides(s, T.HEADING, StatisticJournalType.FLOAT, U.DEG, None,
                       'The current heading.')
        self._provides(s, T.ENERGY_ESTIMATE, StatisticJournalType.FLOAT, U.KJ, S.MAX,
                       'The estimated total energy expended.')
        self._provides(s, T.CALORIE_ESTIMATE, StatisticJournalType.FLOAT, U.KCAL, S.MAX,
                       'The estimated calories burnt.')

    def _set_power(self, s, ajournal):
        power_model = PowerModel(**loads(Constant.from_name(s, self.power_model_ref).at(s).value))
        self.power_model = power_model.expand(s, ajournal.start,
                                              default_owner=Constant, default_activity_group=self.activity_group)
        log.debug(f'Power: {self.power_model_ref}: {self.power_model}')

    def _read_dataframe(self, s, ajournal):
        from ..owners import ActivityReader, ElevationCalculator
        try:
            self._set_power(s, ajournal)
            df = Statistics(s, activity_journal=ajournal, with_timespan=True). \
                by_name(ActivityReader, N.DISTANCE, N.SPEED, N.CADENCE). \
                by_name(ElevationCalculator, N.ELEVATION).df
            ldf = linear_resample_time(df)
            ldf = add_differentials(ldf, max_gap=1.1 * median_dt(df))
            return df, ldf
        except MissingReference as e:
            log.warning(f'Power configuration incorrect ({e})')
        except Exception as e:
            log.warning(f'Failed to generate statistics for power ({ajournal.activity_group.name}): {e}')
            log_current_exception()

    def _calculate_stats(self, s, ajournal, dfs):
        df, ldf = dfs
        total_weight = self.power_model.bike_model.bike_weight + self.power_model.rider_weight
        ldf = add_energy_budget(ldf, total_weight)
        ldf = add_loss_estimate(ldf, total_weight, cda=self.power_model.bike_model.cda,
                                crr=self.power_model.bike_model.crr)
        ldf = add_power_estimate(ldf)
        return df, ldf

    def _copy_results(self, s, ajournal, loader, dfs, fields=(N.POWER_ESTIMATE, N.VERTICAL_POWER)):
        df, ldf = dfs
        self.__add_total_energy(s, ajournal, loader, ldf)
        df = interpolate_to_index(df, ldf, *fields)
        for time, row in df.iterrows():
            for name in fields:
                if name in row and not pd.isnull(row[name]):
                    loader.add_data(name, ajournal, row[name], time)

    def __add_total_energy(self, s, ajournal, loader, ldf):
        if present(ldf, N.POWER_ESTIMATE):
            ldf['tmp'] = ldf[N.POWER_ESTIMATE]
            ldf.loc[ldf['tmp'].isna(), ['tmp']] = 0
            energy = np.trapz(y=ldf['tmp'], x=ldf.index.astype(np.int64) / 1e12)
            loader.add_data(N.ENERGY_ESTIMATE, ajournal, energy, ajournal.start)
            loader.add_data(N.CALORIE_ESTIMATE, ajournal, energy * 0.239006 / self.caloric_eff, ajournal.start)
            ldf.drop(columns=['tmp'], inplace=True)
