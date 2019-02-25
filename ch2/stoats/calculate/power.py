
from collections import namedtuple
from json import loads

import numpy as np
import pandas as pd

from . import DataFrameCalculator
from ...data import activity_statistics, DISTANCE, ELEVATION, SPEED, POW_TWO, TIME, TIMESPAN_ID, AVG, W, POWER
from ...squeal import StatisticJournalFloat, Constant


def d(name): return f'Delta {name}'


def avg(name): return f'Avg {name}'


ENERGY = 'Energy'
LOSS = 'Loss'
SPEED_2 = f'{SPEED}{POW_TWO}'
CDA = 'CdA'
CRR = 'Crr'

AVG_SPEED_2 = avg(SPEED_2)
DELTA_SPEED_2 = d(SPEED_2)
DELTA_TIME = d(TIME)
DELTA_DISTANCE = d(DISTANCE)
DELTA_ELEVATION = d(ELEVATION)
DELTA_SPEED = d(SPEED)
DELTA_ENERGY = d(ENERGY)

Power = namedtuple('Power', 'cda, crr, m, p, g')


class PowerStatistics(DataFrameCalculator):

    def _load_data(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, SPEED, activity_journal_id=ajournal.id, with_timespan=True,
                                     log=self._log, quiet=True)
            return add_differentials(df)
        except Exception as e:
            self._log.warning(f'Failed to generate statistics for power: {e}')

    def _extend_data(self, s, df):
        power_ref = self._assert_karg('power')
        power = Power(**loads(Constant.get(s, power_ref).at(s).value))
        self._log.debug('%s: %s' % (power_ref, power))
        df = add_energy_budget(df, power.m, power.g)
        df = add_loss_estimate(df, power.cda, power.crr, power.p)
        df = add_power_estimate(df)
        return df

    def _copy_results(self, s, ajournal, df, loader):
        for time, row in df.iterrows():
            if not pd.isnull(row[POWER]):
                loader.add(POWER, W, AVG, ajournal.activity_group, ajournal, row[POWER], time,
                           StatisticJournalFloat)


def add_differentials(df):
    df[SPEED_2] = df[SPEED] ** 2

    def diff():
        for _, span in df.groupby(TIMESPAN_ID):
            span = span.copy()
            span[TIME] = span.index
            for col in TIME, DISTANCE, ELEVATION, SPEED, SPEED_2:
                span[d(col)] = span[col].diff()
            span[DELTA_TIME] = span[DELTA_TIME] / np.timedelta64(1, 's')
            avg_speed_2 = [(a**2 + a*b + b**2)/3 for a, b in zip(span[SPEED], span[SPEED][1:])]
            span[AVG_SPEED_2] = [np.nan] + avg_speed_2
            yield span

    return pd.concat(diff())


def add_energy_budget(df, m, g=9.8):
    # if DELTA_ELEVATION is +ve we've gone uphill.  so this is the total amount of energy
    # gained in this segment.
    df[DELTA_ENERGY] = m * (df[DELTA_SPEED_2] / 2 + df[DELTA_ELEVATION] * g)
    return df


def add_cda_estimate(df, p=1.225):
    # https://www.cyclingpowerlab.com/CyclingAerodynamics.aspx
    # assume that all energy lost (-ve gain) is due to air resistance.
    df[CDA] = -df[DELTA_ENERGY] / (p * df[AVG_SPEED_2] * df[DELTA_DISTANCE] * 0.5)
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
    df[POWER] = (df[DELTA_ENERGY] + df[LOSS]) / df[DELTA_TIME]
    return df
