
from logging import getLogger
from math import exp

import scipy as sp

log = getLogger(__name__)


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
    log.debug(f'Exponential decay: {decay}; alpha: {alpha}; period {period} (intervals)')
    data[column] = data[column] / alpha
    data[column] = data[column].ewm(alpha=alpha, adjust=False).mean()


def fit(observed, modeled, initial_data, initial_params, evaluate, *vary,
        tol=0.01, forwards=None, backwards=None):
    '''
    Fit a model to some data.

    The model is parameterised by a namedtuple, with initial values initial_params.
    The evaluate() function takes some data and model parameters and generates the model (in the same data frame).
    The observed and modeled columns in the dataframe are then compared.

    forwards and backwards allow the model parameters to be transformed as necessary.
    forwards goes from the model to the constrained parameters; backwards reverses the transform.
    '''

    if forwards is None: forwards = lambda x: x
    if backwards is None: backwards = lambda x: x

    def objective(args):
        params = initial_params._replace(**backwards(dict(zip(vary, args))))
        data = evaluate(initial_data, params)
        return chisq(observed, modeled, data)

    result = sp.optimize.minimize(objective,
                                  [forwards(initial_params._asdict())[name] for name in vary],
                                  method='Nelder-Mead', tol=tol)
    log.debug(result)
    return initial_params._replace(**backwards(dict(zip(vary, result.x))))


def chisq(observed, modeled, data):
    delta = (data[observed] - data[modeled]).dropna()
    return sum(delta * delta)


def auto_fit(observed, modeled, initial_data, initial_params, evaluate, *vary,
             tol=0.01, forwards=None, backwards=None, max_iter=3):
    count, prev_csq = 0, None
    data = evaluate(initial_data, initial_params)
    csq = chisq(observed, modeled, data)
    while count < max_iter:
        abs_tol = tol * csq
        log.debug(f'Fitting with tol={abs_tol} (chisq {csq})')
        result = fit(observed, modeled, initial_data, initial_params, evaluate, *vary,
                     tol=abs_tol, forwards=forwards, backwards=backwards)
        data = evaluate(initial_data, result)
        csq = chisq(observed, modeled, data)
        if prev_csq is not None and abs(prev_csq - csq) / csq < tol:
            return result
        count, prev_csq = count + 1, csq


def interpolate_to_index(df, extra, *names):
    df['keep'] = True
    both = df.join(extra.loc[:, names], how='outer', sort=True)
    both.loc[both['keep'] != True, ['keep']] = False
    both.interpolate(method='linear', limit_area='inside', inplace=True)
    return both.loc[both['keep']].drop(columns=['keep'])


