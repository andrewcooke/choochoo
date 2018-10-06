
from ..command.args import FORCE, mm
from ..squeal.tables.statistic import StatisticJournal, Statistic


class CleanUnusedStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, force=False, after=None):
        if not force:
            self._log.info('Unused statistics cleaned only with %s' % mm(FORCE))
            return
        n = 0
        with self._db.session_context() as s:
            for statistic in s.query(Statistic).outerjoin(StatisticJournal). \
                    filter(StatisticJournal.statistic_id == None).all():
                self._log.debug('Deleting unused %s' % statistic)
                s.delete(statistic)
                n += 1
        if n:
            self._log.warn('Deleted %d unused Statistics' % n)

