
import scipy as sp


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
        return sp.stats.chisquare(data[observed], data[modeled]).statistic

    result = sp.optimize.minimize(objective,
                                  [forwards(initial_params._asdict())[name] for name in vary],
                                  method='Nelder-Mead', tol=tol)
    return initial_params._replace(**backwards(dict(zip(vary, result.x))))

