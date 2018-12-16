

# http://acooke.org/cute/EfficientS2.html
def expand_max(log, lo, hi, n, f):
    data = [(x, f(x)) for x in (lo + i * (hi - lo) / 4 for i in range(5))]
    for _ in range(n):
        log.info('%s' % data)
        while len(data) > 3:
            w = sum(x*fx for (i, (x, fx)) in enumerate(data)) / sum(fx for (x, fx) in data)
            m = sum(x for (x, fx) in data) / len(data)
            if w > m:
                del data[0]
            else:
                del data[-1]
        x = (data[0][0] + data[1][0]) / 2
        data.insert(1, (x, f(x)))
        x = (data[-2][0] + data[-1][0]) / 2
        data.insert(-1, (x, f(x)))
    x_max, fx_max = None, None
    for (x, fx) in data:
        if x_max is None or fx > fx_max:
            x_max, fx_max = x, fx
    return x_max, fx_max
