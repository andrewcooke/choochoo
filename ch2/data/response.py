
import datetime as dt
from logging import getLogger

from numpy import polyval, polyfit
from pandas import DataFrame, Series
from scipy import optimize

from . import inplace_decay
from ..stoats.names import FITNESS_D_ANY, FATIGUE_D_ANY, like, _d

log = getLogger(__name__)

IMPULSE_3600 = 'Impulse / 3600s'
RESPONSE = 'Response'


# NOTE - almost everything below uses Series, not DataFrame


def sum_to_hour(source, column):
    data = source.resample('1h', label='right').sum()
    data = data.loc[:, [column]]
    data.rename(columns={column: IMPULSE_3600}, inplace=True)
    initial = DataFrame({IMPULSE_3600: 0}, index=[data.index[0] - dt.timedelta(hours=1)])
    data = initial.append(data, sort=True)
    return data


def calc_response(data, log10_period):
    # data is a DataFrame mainly because that's what inplace_decay takes
    response = data.rename(columns={IMPULSE_3600: RESPONSE})  # copy
    inplace_decay(response, RESPONSE, 10 ** log10_period)
    return response[RESPONSE]


def calc_measured(response, performances):
    # we're only interested in the FF model at the times that correspond to performance measurements
    return [response.reindex(index=performance.index, method='nearest')
            for performance in performances]


def calc_predicted(measureds, performances):
    # this is a bit tricky.  we don't know the exact relationship between 'fitness' and how fast we are.
    # all we know is that it should track changes in a useful manner.
    # so there's some arbitrary transform, which could quite easily be different for different routes
    # (no reason 'fitness' should numerically predict the speed on *all* routes, obviously).
    # so we assume that there's an arbitrary linear transform (scaling and offset) from measured speed
    # (or whatever 'performance' is) to 'fitness'.
    # we could fit for the best transform as we fit for the period, but it's more efficient to calculate
    # the 'best' transform for a given period.  this is more efficient because it's equivalent to line fitting
    # (that linear transform is y = ax + b).  so we can call the (fast) line fitting routine in numpy.
    return [Series(polyval(polyfit(performance, measured, 1), performance),
                   performance.index)
            for measured, performance in zip(measureds, performances)]


def calc_residuals(measureds, predicteds, method='L1'):
    if method == 'L1':
        # use L1 scaled by amplitude to be reasonably robust.
        return [abs(measured - predicted) / measured.clip(lower=1e-6)
                for measured, predicted in zip(measureds, predicteds)]
    elif method == 'L2':
        # something like chisq
        return [((measured - predicted).pow(2) / measured.clip(lower=1e-6))
                for measured, predicted in zip(measureds, predicteds)]
    else:
        raise Exception(f'Unknown method ({method}) - use L1 or L2')


def calc_cost(measureds, predicteds, method='L1'):
    residuals = calc_residuals(measureds, predicteds, method=method)
    return sum(sum(residual) for residual in residuals)


def worst_index(predicteds):
    worst, index = None, None
    for i, predicted in enumerate(predicteds):
        bad = max(predicted)
        if index is None or bad > worst:
            worst, index = bad, i
    return index


def reject_worst(log10_period, data, performances, method='L1'):
    response = calc_response(data, log10_period)
    measureds = calc_measured(response, performances)
    predicteds = calc_predicted(measureds, performances)
    residuals = calc_residuals(measureds, predicteds, method=method)
    index = worst_index(predicteds)
    print(f'Dropping value at {residuals[index].idxmax()}')
    performances[index].drop(index=residuals[index].idxmax(), inplace=True)


def fit_period(data, log10_period, performances, method='L1', reject=0, **kargs):
    # data should be a DataFrame with an IMPULSE3600 entry
    # performances should be Series

    result = None

    def cost(log10_period):
        response = calc_response(data, log10_period)
        measureds = calc_measured(response, performances)
        predicteds = calc_predicted(measureds, performances)
        return calc_cost(measureds, predicteds, method=method)

    while True:
        result = optimize.minimize(cost, [log10_period], **kargs)
        log10_period = result.x[0]
        print(10 ** log10_period)
        if not reject: break
        reject_worst(log10_period, data, performances, method=method)
        reject -= 1

    return result


def response_stats(df):
    stats = {}
    for pattern in FITNESS_D_ANY, FATIGUE_D_ANY:
        for name in like(pattern, df.columns):
            stats[_d(name)] = df[name][-1] - df[name][0]
    return stats
