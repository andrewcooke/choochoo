from logging import getLogger

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from .calculate import MultiProcCalculator, IntervalCalculatorMixin
from ...data import statistics
from ...lib import local_time_to_time, format_date
from ...names import HEART_RATE, ALL, REST_HR, BPM, summaries, MIN, MSR
from ...sql import StatisticJournalInteger

log = getLogger(__name__)


class RestHRCalculator(IntervalCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, owner_in='[unused]', schedule='d', **kargs):
        super().__init__(*args, owner_in=owner_in, schedule=schedule, **kargs)

    def _read_data(self, s, interval):
        return statistics(s, HEART_RATE, activity_group=ALL,
                          local_start=interval.start, local_finish=interval.finish)

    def _calculate_results(self, s, interval, df, loader):
        hist = pd.cut(df[HEART_RATE], np.arange(30, 90), right=False).value_counts(sort=False)
        peaks, _ = find_peaks(hist)
        for peak in peaks:
            rest_hr = hist.index[peak].left
            measurements = hist.ilco[rest_hr]
            if measurements > len(df) * 0.01:
                log.debug(f'Rest HR is {rest_hr} with {measurements} values')
                loader.add(REST_HR, BPM, summaries(MIN, MSR), ALL, interval, rest_hr,
                           local_time_to_time(interval.start), StatisticJournalInteger,
                           'The rest heart rate')
                return
            else:
                log.warning(f'Skipping rest HR at {rest_hr} because too few measurements ({measurements}/{len(df)})')
        log.warning(f'Unable to calculate rest HR at {format_date(interval.start)}')

