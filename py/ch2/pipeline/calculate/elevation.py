
from logging import getLogger

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
        self.__create_route_ed(s, ajournal, df)

    def __create_route_ed(self, s, ajournal, df):
        log.debug('Setting route_ed')
        lon_lat_elevation_distance = list(self.__lon_lat_elevation_distance(df))
        if lon_lat_elevation_distance:
            points = [f'ST_MakePoint({lon}, {lat}, {elevation}, {distance})' for lon, lat, elevation, distance
                      in lon_lat_elevation_distance]
            line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
        else:
            log.warning('Empty route?!')
            line = "'LINESTRINGZM EMPTY'::geography"
        table = ajournal.__table__
        update = table.update().values(route_ed=text(line)).where(table.c.id == ajournal.id)
        log.debug(update)
        s.execute(update)

    def __lon_lat_elevation_distance(self, df):
        if N.ELEVATION in df:
            for row in df.dropna().itertuples():
                yield getattr(row, N.LONGITUDE), getattr(row, N.LATITUDE), \
                      getattr(row, N.ELEVATION), getattr(row, N.DISTANCE)
