
import datetime as dt
from logging import getLogger

from bokeh.io import show
from bokeh.plotting import figure
from numpy import polyval, polyfit
from pandas import DataFrame, Series
from scipy import optimize

from ch2.data import inplace_decay
from ch2.data.plot.utils import evenly_spaced_hues

log = getLogger(__name__)

IMPULSE_3600 = 'Impulse / 3600s'
RESPONSE = 'Response'
PREDICTED = 'Predicted'


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


def calc_chisq(measureds, predicteds):
    # use L1 scaled by amplitude to be reasonably robust.
    return sum(sum(abs((measured - predicted) / measured.clip(lower=1e-6)))
               for measured, predicted in zip(measureds, predicteds))


def fit_period(data, log10_period, performances, **kargs):
    # data should be a DataFrame with an IMPULSE3600 entry
    # performances should be Series

    def chisq(log10_period):
        response = calc_response(data, log10_period)
        measureds = calc_measured(response, performances)
        predicteds = calc_predicted(measureds, performances)
        return calc_chisq(measureds, predicteds)

    result = optimize.minimize(chisq, [log10_period], **kargs)
    log.debug(result)
    return result
