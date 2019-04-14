
from math import exp


def inplace_decay(data, column, period):
    # ewm has y(t) = y(t-1) * (1 - alpha) + alpha * x(t)
    # we want y(t) = y(t-1) * exp(-dt/T) + x(t)
    # clearly that won't work exactly, but we can get to within a scaling
    # so compare with y(t-1) * (1 - alpha) + alpha * x(t) * K
    # clearly K = 1/alpha
    # and exp(-dt/T) = 1 - alpha so alpha = 1 - exp(-dt/T)
    # note that this assumes evenly-sampled data of spacing dt
    decay = exp(-1 / period)
    alpha = 1 - decay
    # print(f'decay: {decay}; alpha: {alpha}')
    data[column] = data[column] / alpha
    data[column] = data[column].ewm(alpha=alpha, adjust=False).mean()
