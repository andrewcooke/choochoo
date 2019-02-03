
from sqlalchemy import alias, select, func, and_, not_, exists

from ...squeal import StatisticName, StatisticJournal, StatisticJournalInteger
from ...squeal.database import connect
from ...squeal.utils import tables
from ...stoats.names import CADENCE


def find_freewheel(log, s, cutoff=20):

    t = tables(StatisticName, StatisticJournal, StatisticJournalInteger)
    start = alias(t.StatisticJournal)
    finish = alias(t.StatisticJournal)
    istart = alias(t.StatisticJournalInteger)
    ifinish = alias(t.StatisticJournalInteger)

    nonzeros = exists(). \
        where(and_(t.StatisticJournalInteger.c.value != 0,
                   t.StatisticJournalInteger.c.id == t.StatisticJournal.c.id,
                   t.StatisticJournal.c.statistic_name_id == t.StatisticName.c.id,
                   t.StatisticJournal.c.time > start.c.time,
                   t.StatisticJournal.c.time < finish.c.time))

    delta = select([(finish.c.time - start.c.time).label('delta'),
                    start.c.time.label('start'),
                    finish.c.time.label('finish'),
                    start.c.source_id.label('activity_id')]). \
        select_from(t.StatisticName). \
        where(and_(t.StatisticName.c.name == CADENCE,
                   start.c.statistic_name_id == t.StatisticName.c.id,
                   finish.c.statistic_name_id == t.StatisticName.c.id,
                   start.c.id == istart.c.id,
                   finish.c.id == ifinish.c.id,
                   istart.c.value == 0,
                   ifinish.c.value == 0,
                   start.c.source_id == finish.c.source_id,
                   finish.c.time >= start.c.time + cutoff,
                   ~nonzeros))

    print(delta)


if __name__ == '__main__':
    ns, log, db = connect(['-v 5'])
    with db.session_context() as s:
        find_freewheel(log, s)
