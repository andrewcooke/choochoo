
import datetime as dt
from logging import getLogger

from bokeh.io import show
from bokeh.plotting import figure
from numpy import polyval, polyfit
from pandas import DataFrame
from scipy import optimize

from ch2.data import inplace_decay
from ch2.data.plot.utils import evenly_spaced_hues

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


def calc_measured(response, performances):
    return [response.reindex(index=performance.index, method='nearest')
            for performance in performances]


def calc_predicted(measureds, performances):
    return [DataFrame({PREDICTED: polyval(polyfit(performance.iloc[:, 0], measured.iloc[:, 0], 1),
                                          performance.iloc[:, 0])},
                      index=performance.index)
            for measured, performance in zip(measureds, performances)]


def calc_chisq(measureds, predicteds):
    # use abs(model) as variance to remove bias towards zero scaling for everything
    return sum(sum(abs((measured.iloc[:, 0] - predicted.iloc[:, 0]) / measured.iloc[:, 0].clip(lower=1e-6)))
               for measured, predicted in zip(measureds, predicteds))


def fit_period(data, log10_period, performances, **kargs):

    def chisq(log10_period):
        response = calc_response(data, log10_period)
        measureds = calc_measured(response, performances)
        predicteds = calc_predicted(measureds, performances)
        return calc_chisq(measureds, predicteds)

    result = optimize.minimize(chisq, [log10_period], **kargs)
    log.debug(result)
    return result
