
from collections import namedtuple
from logging import getLogger

# hide from imports of this package
import numpy as _np
import scipy as _sp
from math import pi
from pandas import to_numeric

import ch2.common.args
from .frame import median_dt
from .lib import fit, inplace_decay
from ..lib.data import tmp_name, safe_first
from ..names import Names as N

log = getLogger(__name__)
RAD_TO_DEG = 180 / pi


def add_differentials(df, max_gap=None):
    return _add_differentials(df, N.SPEED, N.DISTANCE, N.ELEVATION, N.SPEED, N.SPEED_2, max_gap=max_gap)


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
    df[N.CDA] = -df[N.DELTA_ENERGY] / (p * df[N.AVG_SPEED_2] * df[N.DELTA_DISTANCE] * 0.5)
    return df


def add_crr_estimate(df, m, g=9.8):
    # assume that all energy lost is due to rolling resistance
    df[N.CRR] = -df[N.DELTA_ENERGY] / (df[N.DELTA_DISTANCE] * m * g)
    return df


@safe_first
def add_loss_estimate(df, m, cda=0.45, crr=0, p=1.225, g=9.8):
    # this is the energy spent on air and rolling resistance
    df[N.LOSS] = (cda * p * df[N.AVG_SPEED_2] * 0.5 + crr * m * g) * df[N.DELTA_DISTANCE]
    return df


@safe_first
def add_power_estimate(df):
    # power input must balance the energy budget.
    df[N.VERTICAL_POWER] = df[N.DELTA_ENERGY] / df[N.DELTA_TIME].dt.total_seconds()
    df[N.VERTICAL_POWER].clip(lower=0, inplace=True)
    df[N.POWER_ESTIMATE] = (df[N.DELTA_ENERGY] + df[N.LOSS]) / df[N.DELTA_TIME].dt.total_seconds()
    df[N.POWER_ESTIMATE].clip(lower=0, inplace=True)
    # if N.CADENCE in df.columns:
    #     df.loc[df[N.CADENCE] < 1, [N.POWER_ESTIMATE]] = 0.0
    if any(df[N.POWER_ESTIMATE].isna()):
        df.loc[df[N.POWER_ESTIMATE].isna(), [N.POWER_ESTIMATE]] = 0.0
        # need to coerce because dtype is object
        df[N.POWER_ESTIMATE] = df[N.POWER_ESTIMATE].apply(to_numeric, errors='coerce')
    energy = (df[N.POWER_ESTIMATE].iloc[1:] * df[N.DELTA_TIME].iloc[1:]).cumsum()
    df[N.ENERGY] = 0.0
    df.loc[:, [N.ENERGY]].iloc[1:] = energy
    # A value is trying to be set on a copy of a slice from a DataFrame.
    # Try using .loc[row_indexer,col_indexer] = value instead
    # df.iloc[1:][N.ENERGY] = energy
    return df


def evaluate(df, model, quiet=True):
    # used in fitting
    if not quiet: log.debug(f'Evaluating {model}')
    df = add_energy_budget(df, model.bike_weight)
    df = add_loss_estimate(df, model.bike_weight, cda=model.cda, crr=model.crr)
    df = add_power_estimate(df)
    return df
