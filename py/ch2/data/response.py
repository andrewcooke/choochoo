
import datetime as dt
import re
from logging import getLogger
from math import exp

import numpy as np
from pandas import DataFrame, Series
from scipy import optimize

from ch2.data.lib import decay_params
from . import inplace_decay
from ..stats.names import FITNESS_D_ANY, FATIGUE_D_ANY, like, _delta, FITNESS, RECOVERY_D, EARNED_D, PLATEAU_D

log = getLogger(__name__)

IMPULSE_3600 = 'Impulse / 3600s'
RESPONSE = 'Response'
LOG10_PERIOD, LOG10_START = 0, 1


# Almost everything below uses Series, not DataFrame
# Currently model params are log10_period (hours) and log10_start (initial FF value)


def sum_to_hour(source, column):
    data = source.resample('1h', label='right').sum()
    data = data.loc[:, [column]]
    data.rename(columns={column: IMPULSE_3600}, inplace=True)
    initial = DataFrame({IMPULSE_3600: 0}, index=[data.index[0] - dt.timedelta(hours=1)])
    data = initial.append(data, sort=True)
    return data


def calc_response(data, params):
    # data is a DataFrame mainly because that's what inplace_decay takes
    response = data.rename(columns={IMPULSE_3600: RESPONSE})  # copy
    period = 10 ** params[LOG10_PERIOD]
    if len(params) > LOG10_START:
        decay, alpha = decay_params(period)
        # correct by alpha so that the value matches the plot (see decay_inplace)
        start = 10 ** params[LOG10_START] * alpha
        # we replace the very first value which is strictly cheating, but there are so many...
        response.at[response.index[0], RESPONSE] = start
    inplace_decay(response, RESPONSE, period)
    return response[RESPONSE]


def restrict_response(response, performances):
    # we're only interested in the FF model at the times that correspond to performance measurements
    return [response.reindex(index=performance.index, method='nearest')
            for performance in performances]


def calc_observed(measureds, performances):
    # this is a bit tricky.  we don't know the exact relationship between 'fitness' and how fast we are.
    # all we know is that it should track changes in a useful manner.
    # so there's some arbitrary transform, which could quite easily be different for different routes
    # (no reason 'fitness' should numerically predict the speed on *all* routes, obviously).
    # so we assume that there's an arbitrary linear transform (scaling and offset) from measured speed
    # (or whatever 'performance' is) to 'fitness'.
    # we could fit for the best transform as we fit for the period, but it's more efficient to calculate
    # the 'best' transform for a given period.  this is more efficient because it's equivalent to line fitting
    # (that linear transform is y = ax + b).  so we can call the (fast) line fitting routine in numpy.
    return [Series(np.polyval(np.polyfit(performance, measured, 1), performance),
                   performance.index)
            for measured, performance in zip(measureds, performances)]


def calc_residuals(models, observations, method='L1'):
    # -ve when observation less than model
    if method == 'L1':
        # use L1 scaled by amplitude to be reasonably robust.
        return [(observation - model) / model.clip(lower=1e-6)
                for model, observation in zip(models, observations)]
    elif method == 'L2':
        # something like chisq
        return [(np.sign(observation - model) * (observation - model).pow(2) / model.clip(lower=1e-6))
                for model, observation in zip(models, observations)]
    else:
        raise Exception(f'Unknown method ({method}) - use L1 or L2')


def calc_cost(model, observation, method='L1'):
    residuals = calc_residuals(model, observation, method=method)
    return sum(sum(np.abs(residual)) for residual in residuals)


def worst_residual(residuals, threshold=None):
    i, t, worst = None, None, None
    for index, residual in enumerate(residuals):
        bad = max(residual)
        if bad > threshold and (worst is None or bad > worst):
            worst, i, t = bad, index, residual.idxmax()
    if worst:
        log.debug(f'Worst residual magnitude {worst} at {t}')
    else:
        log.debug('No worst residual found')
    return i, t, worst


def fix_residuals(residuals, threshold=None):
    try:
        pos, neg = np.abs(threshold)
        log.debug(f'Scaling residuals to weight lower by {pos}:{neg}')
        for residual in residuals:
            residual.loc[residual < 0] = residual.loc[residual < 0].abs() * pos / neg
        return residuals, pos
    except TypeError:
        return [residual.abs() for residual in residuals], 0 if threshold is None else threshold


def reject_worst_inplace(params, data, performances, method='L1', threshold=None):
    response = calc_response(data, params)
    measureds = restrict_response(response, performances)
    predicteds = calc_observed(measureds, performances)
    residuals = calc_residuals(measureds, predicteds, method=method)
    residuals, threshold = fix_residuals(residuals, threshold=threshold)
    i, t, worst = worst_residual(residuals, threshold=threshold)
    if t:
        print(f'Dropping {worst} at {t}')
        performances[i].drop(index=t, inplace=True)
    return i, t


def fmt_params(params):
    text = f'Period {10 ** params[0] / 24:.1f}'
    if len(params) > 1:
        text += f'; Start {10 ** params[1]:.1f}'
    return text


def fit_ff_params(data, params, performances, method='L1', max_reject=0, threshold=None, **kargs):
    # data should be a DataFrame with an IMPULSE3600 entry
    # performances should be Series
    # threshold can be None, a value, or a pair.  a pair gives +ve and -ve thresholds

    result, rejected = None, []

    def cost(params):
        response = calc_response(data, params)
        restricted = restrict_response(response, performances)
        observed = calc_observed(restricted, performances)
        return calc_cost(restricted, observed, method=method)

    while True:
        result = optimize.minimize(cost, params, **kargs)
        print(fmt_params(result.x))
        print(f'Currently have {len(rejected)} dropped points (max {max_reject})')
        if len(rejected) >= max_reject:
            return result, rejected
        i, t = reject_worst_inplace(params, data, performances, method=method, threshold=threshold)
        if t is None:
            return result, rejected
        rejected.append((i, t))


def response_stats(df, prev_secs):
    from math import log
    digits = re.compile(r'(\d+)')
    stats = {}
    for pattern in FITNESS_D_ANY, FATIGUE_D_ANY:
        for name in like(pattern, df.columns):
            lower, higher = df[name][0], df[name][-1]
            delta = higher - lower
            stats[_delta(name)] = delta
            days = int(digits.search(name).group(1))
            tau = days * 24 * 60 * 60
            # this is the time needed for the value to return to where it was before the activity
            # so for fitness it's kinda the time 'bought' within which you're not getting worse and
            # for fatigue it's the recovery time.
            revert = tau * log(1 + delta / lower)
            if FITNESS in name:
                stats[EARNED_D % days] = revert
                if prev_secs:
                    # this was an experiment.  if you exercise regularly at the same intensity then you
                    # will tend to a certain fitness level.  this is an estimate of that level, assuming
                    # that activities repeat at the same interval as the time from the previous activity.
                    # it was a cute idea, but turns out to be way too noisy to be useful.
                    plateau = delta / (exp(prev_secs / tau) - 1)
                    stats[PLATEAU_D % days] = plateau
            else:
                stats[RECOVERY_D % days] = revert
    return stats
