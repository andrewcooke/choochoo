from logging import getLogger

from scipy import optimize

log = getLogger(__name__)


def fit(params, data, model, cost, vary=None, strategy=None, bounds=None, **kargs):

    if vary is None: vary = list(params.keys())
    if strategy is None: strategy = immediate

    for to_vary in strategy(vary):
        log.info(f'Varying {",".join(to_vary)}')

        def func(x):
            for (name, value) in zip(to_vary, x):
                params[name] = value
            return cost(model(params, data))

        x0 = [params[name] for name in to_vary]
        bds = [bounds.get(name, (None, None)) for name in to_vary] if bounds else None
        result = optimize.minimize(func, x0, bounds=bds, method='Powell', **kargs)

        if not result.success:
            log.warning(f'Optimize failed: {result.message}')

        for (name, value) in zip(to_vary, result.x):
            log.info(f'{name} = {value}')
            params[name] = value

    return params


def immediate(vary):
    yield vary


def progressive(vary):
    to_vary = []
    for name in vary:
        to_vary.append(name)
        yield to_vary
