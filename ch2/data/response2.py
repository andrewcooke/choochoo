
import datetime as dt
from logging import getLogger

from numpy import polyval, polyfit
from pandas import DataFrame
from scipy import optimize

from ch2.data import inplace_decay

log = getLogger(__name__)

IMPULSE_3600 = 'Impulse / 3600s'
RESPONSE = 'Response'


def sum_to_hour(source, column):
    data = source.resample('1h', label='right').sum()
    data = data.loc[:, [column]]
    data.rename(columns={column: IMPULSE_3600}, inplace=True)
    initial = DataFrame({IMPULSE_3600: 0,}, index=[data.index[0] - dt.timedelta(hours=1)])
    data = initial.append(data, sort=True)
    return data


def calc_response(data, log10_period):
    response = data.rename(columns={IMPULSE_3600: RESPONSE})
    inplace_decay(response, RESPONSE, 10 ** log10_period)
    return response


def calc_chisq(data, performance):
    # extract the response data at the points we are going to compare
    measured_y = data.reindex(index=performance.index, method='nearest')
    # find the best linear transform to the observed data
    # so we're going to compare response with a * speed + b for some a and b
    predicted_y = polyval(performance.iloc[:, 0],
                          polyfit(performance.iloc[:, 0], measured_y.iloc[:, 0], 1))
    # use abs(model) as variance to remove bias towards zero scaling for everything
    return sum((y1 - y2)**2 / abs(y2) for y1, y2 in zip(measured_y.iloc[:, 0], predicted_y))


def fit_period(data, log10_period, performances, **kargs):

    def chisq(log10_period):
        response = calc_response(data, log10_period)
        return sum(calc_chisq(response, performance) for performance in performances)

    result = optimize.minimize(chisq, [log10_period], **kargs)
    log.debug(result)
    return result
