
from time import sleep

from bokeh.layouts import column, row
from bokeh.models import Div

from ..plot import simple_map
from ..server import Page, singleton_server
from ...config import config
from ...data import activity_statistics
from ...squeal import ActivityJournal
from ...stoats.display.nearby import nearby_any_time, constraints
from ...stoats.names import SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y

MAP_SIDE = 100
MAPS_PER_ROW = 10


def similar(log, s, aj):
    x = list(tiles(log, s, aj))
    rows = []
    for i in range(0, len(x), MAPS_PER_ROW):
        rows.append(row(*x[i:i+MAPS_PER_ROW]))
    return column(*rows)


def tiles(log, s, compare):
    xy_compare = xy(log, s, compare)
    for c in constraints(s):
        for aj, nb in nearby_any_time(s, compare, c):
            yield tile(log, s, aj, compare, xy_compare, nb)


def tile(log, s, aj, compare, xy_compare, nb):
    return column(simple_map(MAP_SIDE, xy(log, s, aj), xy_compare),
                  caption(aj, compare, nb))


def caption(aj, compare, nb):
    return Div(text='<p><a href="activity_journal?id=%d&amp;compare=%d">%s %d%%</a></p>' %
                    (aj.id, compare.id, aj.start.strftime('%y-%m-%d'), 100 * nb.similarity),
               width=MAP_SIDE)


def xy(log, s, aj, every=10):
    return activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                               activity_journal_id=aj.id, log=log).iloc[::every, :]


class ActivitySimilarityPage(Page):

    def create(self, s, id=None, **kargs):
        aj1 = s.query(ActivityJournal). \
            filter(ActivityJournal.id == self.single_int_param('id', id)).one()
        title = 'Similar to %s' % aj1.name
        return {'header': title, 'title': title}, similar(self._log, s, aj1)


if __name__ == '__main__':
    '''
    for testing - can be run from within the IDE which makes it easier to display data, set breakpoints, etc.
    '''
    from .activity_journal import ActivityJournalPage
    log, db = config('-v 5')
    server = singleton_server(log, {'/activity_similarity': ActivitySimilarityPage(log, db),
                                    '/activity_journal': ActivityJournalPage(log, db)})
    try:
        with db.session_context() as s:
            # aj1 = ActivityJournal.at_date(s, '2019-01-25')[0]
            # aj2 = ActivityJournal.at_date(s, '2019-01-23')[0]
            # path = '/activity_journal?id=%d&compare=%d' % (aj1.id, aj2.id)
            aj1 = ActivityJournal.at_date(s, '2019-01-27')[0]
            path = '/activity_similarity?id=%d' % aj1.id
            server.show(path)
        log.info('Crtl-C to exit')
        while True:
            sleep(1)
    finally:
        server.stop()

