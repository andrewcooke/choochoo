
import datetime as dt
from collections import namedtuple

import pandas as pd

from .lib import inplace_decay

IMPULSE_3600 = 'Impulse / 3600s'
DecayModel = namedtuple('DecayModel', 'start, zero, scale, period, input, output')


def pre_calc(source, model, start=None, finish=None, target=None):
    # sum into 1-hour blocks (the decay is much longer period so this has little effect on accuracy
    # but saves time) and then add target indices
    if target is not None:
        if start:
            start = min(start, target.index[0])
        else:
            start = target.index[0]
        if finish:
            finish = max(finish, target.index[-1])
        else:
            finish = target.index[-1]
    start, finish = start.round('1H'), (finish + dt.timedelta(hours=1)).round('1H')
    data = source.resample('1h', label='right').sum()
    data = data.loc[:, [model.input]]
    data.rename(columns={model.input: IMPULSE_3600}, inplace=True)
    times = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq='1H'), columns=[model.output])
    data = data.join(times, how='outer', sort=True)
    t0 = data.index[0]
    initial = pd.DataFrame({IMPULSE_3600: model.start, model.output: 0}, index=[t0 - dt.timedelta(hours=1)])
    data = initial.append(data, sort=True)
    data.fillna(0, inplace=True)
    return data


def calc(data, model):
    data[model.output] = data[IMPULSE_3600] * model.scale
    inplace_decay(data, model.output, model.period)
    return data
