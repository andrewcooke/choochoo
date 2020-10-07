from logging import getLogger

import pandas as pd
from sqlalchemy import text

from .utils import ProcessCalculator, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import LoaderMixin
from ...common.math import is_nan
from ...data import Statistics
from ...data.elevation import smooth_elevation
from ...data.frame import present
from ...names import N, T, U
from ...sql import StatisticJournalFloat, StatisticJournalType

log = getLogger(__name__)


class ElevationCalculator(LoaderMixin, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, ProcessCalculator):

    def __init__(self, *args, smooth=3, **kargs):
        self.smooth = smooth
        super().__init__(*args, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self._provides(s, T.ELEVATION, StatisticJournalType.FLOAT, U.M, None,
                       'An estimate of elevation (may come from various sources).')
        self._provides(s, T.GRADE, StatisticJournalType.FLOAT, U.PC, None,
                       'The gradient of the smoothed SRTM1 elevation.')

    def _read_dataframe(self, s, ajournal):
        from ..owners import SegmentReader
        try:
            return Statistics(s, activity_journal=ajournal, with_timespan=True). \
                by_name(SegmentReader, N.LATITUDE, N.LONGITUDE, N.DISTANCE,
                        N.RAW_ELEVATION, N.ELEVATION, N.ALTITUDE).df
        except Exception as e:
            log.warning(f'Failed to generate statistics for elevation: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        if not present(df, N.ELEVATION):
            if present(df, N.RAW_ELEVATION):
                df = smooth_elevation(df, smooth=self.smooth)
            elif present(df, N.ALTITUDE):
                log.warning(f'Using {N.ALTITUDE} as {N.ELEVATION}')
                df[N.ELEVATION] = df[N.ALTITUDE]
            return df
        else:
            return None

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            if N.ELEVATION in row and not is_nan(row[N.ELEVATION]):
                loader.add_data(N.ELEVATION, ajournal, row[N.ELEVATION], time)
            if N.GRADE in row and not is_nan(row[N.GRADE]):
                loader.add_data(N.GRADE, ajournal, row[N.GRADE], time)
        self.__create_routes(s, ajournal, df)

    def __create_routes(self, s, ajournal, df):
        self.__create_route(s, ajournal, df, 'route_ed', self.__lon_lat_elevation_distance)
        self.__create_route(s, ajournal, df, 'route_edt', self.__lon_lat_elevation_distance_time)

    def __create_route(self, s, ajournal, df, name, selector):
        log.debug(f'Setting {name}')
        xyzm = list(selector(df, ajournal))
        if xyzm:
            points = [f'ST_MakePoint({x}, {y}, {z}, {m})' for x, y, z, m in xyzm]
            line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
        else:
            log.warning(f'Empty {name}')
            line = "'LINESTRINGZM EMPTY'::geography"
        table = ajournal.__table__
        update = table.update().values(**{name: text(line)}).where(table.c.id == ajournal.id)
        # log.debug(update)
        s.execute(update)

    def __lon_lat_elevation_distance(self, df, ajournal):
        if N.ELEVATION in df:
            for row in df.dropna().itertuples():
                yield getattr(row, N.LONGITUDE), getattr(row, N.LATITUDE), \
                      getattr(row, N.ELEVATION), getattr(row, N.DISTANCE)

    def __lon_lat_elevation_distance_time(self, df, ajournal):
        if N.ELEVATION in df:
            for row in df.dropna().itertuples():
                time = (row.Index - ajournal.start).total_seconds()
                distance = getattr(row, N.DISTANCE)
                # 15 digits available.
                # 6+1 for time = 999999.9s = 10 days
                # 6+1 for distance = 999999.9m = 1000km
                dt = onedp(distance) * 1e7 + onedp(time)
                yield getattr(row, N.LONGITUDE), getattr(row, N.LATITUDE), \
                      getattr(row, N.ELEVATION), dt


def onedp(x):
    return int(10 * x + 0.5) / 10


def expand_distance_time(df, key, t0):
    df[N.DISTANCE] = (df[key] / 1e7).round(1)
    df[N.TIME] = df[key] - df[N.DISTANCE] * 1e7
    df[N.TIME] = pd.to_timedelta(df[N.TIME], 'seconds') + t0
    return df.drop(columns=[key])
