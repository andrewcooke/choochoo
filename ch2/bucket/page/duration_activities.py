
from time import sleep

from bokeh.layouts import column, row
from bokeh.models import Div

from ..data_frame import xy
from ..plot import simple_map
from ..server import Page, default_singleton_server, target_link
from ...config import config
from ...lib.date import to_duration, add_date, local_date_to_time
from ...squeal import ActivityJournal

MAP_SIDE = 100
MAPS_PER_ROW = 10


def duration(log, s, start, finish):
    x = list(tiles(log, s, start, finish))
    rows = []
    for i in range(0, len(x), MAPS_PER_ROW):
        rows.append(row(*x[i:i+MAPS_PER_ROW]))
    return column(*rows)


def tiles(log, s, start, finish):
    for aj in s.query(ActivityJournal). \
            filter(ActivityJournal.start >= local_date_to_time(start),
                   ActivityJournal.start < local_date_to_time(finish)).all():
        yield tile(log, s, aj)


def tile(log, s, aj):
    return column(simple_map(MAP_SIDE, xy(log, s, aj)),
                  caption(aj))


def caption(aj):
    from .activity_details import ActivityDetailsPage
    return Div(text='<p>' +
                    target_link('%s?id=%d' % (ActivityDetailsPage.PATH, aj.id,), aj.start.strftime('%Y-%m-%d')) +
                    '</p>',
               width=MAP_SIDE)


class DurationActivitiesPage(Page):

    PATH = '/duration_activities'

    def create(self, s, start=None, finish=None, period=None, **kargs):
        if finish and period:
            raise Exception("Specify finish or period (not both)")
        start = self.single_date_param('start', start)
        if finish:
            finish = self.single_time_param('finish', finish)
        else:
            period = self._single_param(to_duration, 'period', period)
            finish = add_date(start, period)
        title = '%s - %s' % (start.strftime("%Y-%m-%d"), finish.strftime("%Y-%m-%d"))
        return {'header': title, 'title': title}, duration(self._log, s, start, finish)


if __name__ == '__main__':
    '''
    for testing - can be run from within the IDE which makes it easier to display data, set breakpoints, etc.
    '''
    log, db = config('-v 5')
    server = default_singleton_server(log, db)
    try:
        with db.session_context() as s:
            path = '%s?start=2018-01-01&period=1y' % DurationActivitiesPage.PATH
            server.show(path)
        log.info('Crtl-C to exit')
        while True:
            sleep(1)
    finally:
        server.stop()

