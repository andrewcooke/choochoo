from logging import getLogger

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from .utils import MultiProcCalculator, IntervalCalculatorMixin
from ..pipeline import OwnerInMixin
from ...data import Statistics
from ...lib import format_date, local_date_to_time
from ...names import Titles, Summaries as S, Units, Names
from ...sql import StatisticJournalInteger

log = getLogger(__name__)


class RestHRCalculator(OwnerInMixin, IntervalCalculatorMixin, MultiProcCalculator):

    '''
    Used to calculate rest HR from quartiles, but it was never clear we had *the* rest value rather
    than some general lower value.

    This way - by looking for the first peak that's not noise - we are finding something that perhaps
    is more meaningful.  It's a low heart rate that you spent a fair amount of time at.
    '''

    def __init__(self, *args, schedule='d', **kargs):
        super().__init__(*args, schedule=schedule, **kargs)

    # def _missing(self, s):
    #     return super()._missing(s)

    def _read_data(self, s, interval):
        return Statistics(s, start=local_date_to_time(interval.start),
                          finish=local_date_to_time(interval.finish)). \
            by_name(self.owner_in, Names.HEART_RATE).df

    def _calculate_results(self, s, interval, df, loader):
        if not df.empty:
            hist = pd.cut(df[Names.HEART_RATE], np.arange(30, 90), right=False).value_counts(sort=False)
            peaks, _ = find_peaks(hist)
            for peak in peaks:
                rest_hr = hist.index[peak].left
                measurements = hist.loc[rest_hr]
                if measurements > len(df) * 0.01:
                    log.debug(f'Rest HR is {rest_hr} with {measurements} values')
                    # conversion to int as value above is numpy int64
                    loader.add(Titles.REST_HR, Units.BPM, S.join(S.MIN, S.MSR), interval,
                               int(rest_hr), local_date_to_time(interval.start), StatisticJournalInteger,
                               'The rest heart rate')
                    return
                else:
                    log.debug(f'Skipping rest HR at {rest_hr} because too few measurements ({measurements}/{len(df)})')
        log.warning(f'Unable to calculate rest HR at {format_date(interval.start)}')

