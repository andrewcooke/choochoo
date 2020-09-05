from typing import SupportsFloat

from math import isnan


def is_nan(value):
    return value is None or (isinstance(value, SupportsFloat) and isnan(value))
