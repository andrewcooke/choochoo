
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
LOG10_PERIOD, LOG10_START = 0, 1


# NOTE - almost everything below uses Series, not DataFrame


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
    if len(params) > LOG10_START:
        # we replace the very first value which is strictly cheating, but there are so many...
        response.at[response.index[0], [RESPONSE]] = 10 ** params[LOG10_START]
    inplace_decay(response, RESPONSE, 10 ** params[LOG10_PERIOD])
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


def worst_index(residuals):
    worst, index = None, None
    for i, residual in enumerate(residuals):
        bad = max(residual)
        if index is None or bad > worst:
            worst, index = bad, i
    return index


def reject_worst_inplace(params, data, performances, method='L1'):
    response = calc_response(data, params)
    measureds = calc_measured(response, performances)
    predicteds = calc_predicted(measureds, performances)
    residuals = calc_residuals(measureds, predicteds, method=method)
    index = worst_index(residuals)
    print(f'Dropping value at {residuals[index].idxmax()}')
    performances[index].drop(index=residuals[index].idxmax(), inplace=True)
    return index, residuals[index].idxmax()


def fmt_params(params):
    text = f'Period {10 ** params[0] / 24:.1f}'
    if len(params) > 1:
        text += f'; Start {10 ** params[1]:.1f}'
    return text


def fit_ff_params(data, params, performances, method='L1', reject=0, **kargs):
    # data should be a DataFrame with an IMPULSE3600 entry
    # performances should be Series

    result, rejected = None, []

    def cost(params):
        response = calc_response(data, params)
        measureds = calc_measured(response, performances)
        predicteds = calc_predicted(measureds, performances)
        return calc_cost(measureds, predicteds, method=method)

    while True:
        result = optimize.minimize(cost, params, **kargs)
        print(fmt_params(result.x))
        if not reject: break
        rejected.append(reject_worst_inplace(params, data, performances, method=method))
        reject -= 1

    return result, rejected


def response_stats(df):
    stats = {}
    for pattern in FITNESS_D_ANY, FATIGUE_D_ANY:
        for name in like(pattern, df.columns):
            stats[_d(name)] = df[name][-1] - df[name][0]
    return stats
