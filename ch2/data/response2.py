
import datetime as dt
from logging import getLogger

from numpy import polyval, polyfit
from pandas import DataFrame
from scipy import optimize

from ch2.data import inplace_decay

log = getLogger(__name__)

IMPULSE_3600 = 'Impulse / 3600s'
RESPONSE = 'Response'
PREDICTED = 'Predicted'


def sum_to_hour(source, column):
    data = source.resample('1h', label='right').sum()
    data = data.loc[:, [column]]
    data.rename(columns={column: IMPULSE_3600}, inplace=True)
    initial = DataFrame({IMPULSE_3600: 0}, index=[data.index[0] - dt.timedelta(hours=1)])
    data = initial.append(data, sort=True)
    return data


def calc_response(data, log10_period):
    response = data.rename(columns={IMPULSE_3600: RESPONSE})
    inplace_decay(response, RESPONSE, 10 ** log10_period)
    return response


def calc_predicted(response, performances):
    for performance in performances:
        # extract the response data at the points we are going to compare
        measured_y = response.reindex(index=performance.index, method='nearest')
        predicted_y = polyval(polyfit(performance.iloc[:, 0], measured_y.iloc[:, 0], 1),
                              performance.iloc[:, 0])
        yield DataFrame({PREDICTED: predicted_y}, index=performance.index)


def calc_chisq(response, predicted):
    # use abs(model) as variance to remove bias towards zero scaling for everything
    return sum((y1 - y2)**2 / abs(y2) for y1, y2 in zip(response.iloc[:, 0], predicted.iloc[:, 0]))


def fit_period(data, log10_period, performances, **kargs):

    def chisq(log10_period):
        response = calc_response(data, log10_period)
        return sum(calc_chisq(response, predicted)
                   for predicted in calc_predicted(response, performances))

    result = optimize.minimize(chisq, [log10_period], **kargs)
    log.debug(result)
    return result
