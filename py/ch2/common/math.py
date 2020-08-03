from math import isnan


def is_nan(value):
    return value is None or isnan(value)
