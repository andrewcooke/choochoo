
from abc import abstractmethod
from logging import getLogger
from sys import exc_info
from traceback import format_tb

from psutil import cpu_count
from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from .worker import Workers
from .. import Statistics
from ...load import StatisticJournalLoader
from ....command.args import STATISTICS, WORKER, mm
from ....lib.date import time_to_local_time, local_time_to_time
from ....squeal import Timestamp, ActivityJournal, StatisticName, StatisticJournal
from ....squeal.types import short_cls, long_cls


log = getLogger(__name__)
CPU_FRACTION = 0.9
MAX_REPEAT = 3


class MultiProcCalculator(Statistics):

    def __init__(self, *args, owner_out=None, force=False, start=None, finish=None,
                 overhead=1, cost_calc=0, cost_write=1, n_cpu=None, worker=None, id=None, **kargs):
        super().__init__(*args, **kargs)
        self.owner_out = owner_out or self  # the future owner of any calculated statistics
        self.force = force  # delete data (force re-calculation)?
        self.start = start  # optional start local time (always present for workers)
        self.finish = finish  # optional finish local time (always present for workers)
        self.overhead = overhead  # next three args are used to decide if workers are needed
        self.cost_calc = cost_calc  # see _cost_benefit for full details
        self.cost_write = cost_write  # defaults guarantee a single thread
        self.n_cpu = max(1, int(cpu_count() * CPU_FRACTION)) if n_cpu is None else n_cpu  # number of cpus available
        self.worker = worker  # if True, then we're in a sub-process
        self.id = id  # the id for the pipeline entry in the database (passed to sub-processes)

    # todo - move up inheritance hierarchy when not using kargs elsewhere
    def _start_finish(self, type=None):
        start, finish = self.start, self.finish
        if type:
            if start: start = type(start)
            if finish: finish = type(finish)
        return start, finish

    def run(self):

        with self._db.session_context() as s:

            if self.force:
                if self.worker:
                    log.warning('Worker deleting data')
                self._delete(s)

            missing = self._missing(s)

        if self.worker:
            self._run_all(s, missing)
        elif not missing:
            log.info(f'No missing statistics for {short_cls(self)}')
        else:
            n_total, n_parallel = self.__cost_benefit(missing, self.n_cpu)
            if n_parallel < 2:
                self._run_all(s, missing)
            else:
                self.__spawn(s, missing, n_total, n_parallel)

    def _run_all(self, s, missing):
        for time_or_date in missing:
            self._run_one(s, time_or_date)
            s.commit()

    @abstractmethod
    def _missing(self, s):
        raise NotImplementedError()

    @abstractmethod
    def _delete(self, s):
        raise NotImplementedError()

    @abstractmethod
    def _run_one(self, s, time_or_date):
        raise NotImplementedError()

    def __cost_benefit(self, missing, n_cpu):

        # is it worth using workers?  there's some cost in starting them up and there will be contention
        # in accessing the database.
        # let's say COST (for one missing time) is COST_WRITE + COST_CALC (ignoring units).
        # if we have N_MISSING tasks divided into N_TOTAL workloads amongst N_PARALLEL workers
        # then we have these conditions (in order):
        #   N_PARALLEL * (COST_WRITES/ COST) <= 1 so that we avoid blocking completely on writes
        #   N_PARALLEL <= N_CPU
        #   N_TOTAL <= N_MISSING / N_PARALLEL
        #   (N_MISSING / N_TOTAL) * COST > OVERHEAD so we're not wasting our time
        #   N_TOTAL <= N_PARALLEL * MAX_REPEAT because we want large batches, but not too large
        # really we should include estimates of disk and cpu speed here, in which case we need to separate
        # out COST_READ too (currently folded into COST_CALC).

        log.debug(f'Batching for n_cpu={n_cpu}, overhead={self.overhead}, '
                        f'cost_writes={self.cost_write} cost_calc={self.cost_calc}')
        n_missing = len(missing)
        cost = self.cost_write + self.cost_calc
        limit = cost / self.cost_write
        log.debug(f'Limit on parallel workers from database contention is {limit:3.1f}')
        log.debug(f'Limit on parallel workers from CPU count is {n_cpu:d}')
        n_parallel = int(min(limit, n_cpu))
        n_total = int((n_missing + n_parallel - 1) / n_parallel)
        log.debug(f'Limit on total workers from work available is {n_total:d}')
        limit = cost * n_missing / self.overhead
        log.debug(f'Limit on total workers from overhead is {limit:3.1f}')
        n_total = min(n_total, int(limit))
        limit = n_parallel * MAX_REPEAT
        log.debug(f'Limit on total workers to boost batch size is {limit:d}')
        n_total = min(n_total, limit)
        log.info(f'Threads: {n_total}/{n_parallel}')
        return n_total, n_parallel

    def __spawn(self, s, missing, n_total, n_parallel):

        # unfortunately we have to do things with contiguous dates, which may introduce systematic
        # errors in our timing estimates

        n_missing = len(missing)
        workers = Workers(s, n_parallel, self.owner_out,
                          f'{{ch2}} -v0 -l {{log}} {STATISTICS} {mm(WORKER)} {self.id}')
        start, finish = None, -1
        for i in range(n_total):
            start = finish + 1
            finish = int(0.5 + (i+1) * (n_missing-1) / n_total)
            if start > finish: raise Exception('Bad chunking logic')
            s, f = time_to_local_time(missing[start]), time_to_local_time(missing[finish])
            log.info(f'Starting worker for {s} - {f}')
            args = f'"{s}" "{f}"'
            workers.run(args)
        workers.wait()


class DataFrameCalculator(MultiProcCalculator):

    def _run_one(self, s, time_or_date):
        try:
            source = self._get_source(s, time_or_date)
            data = self._load_data(s, source)
            stats = self._calculate_stats(s, source, data)
            loader = StatisticJournalLoader(log, s, self.owner_out)
            self._copy_results(s, source, loader, stats)
            loader.load()
        except Exception as e:
            log.warning(f'No statistics on {time_or_date} ({e})')
            log.debug('\n' + ''.join(format_tb(exc_info()[2])))

    @abstractmethod
    def _get_source(self, s, time_or_date):
        raise NotImplementedError()

    @abstractmethod
    def _load_data(self, s, source):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_stats(self, s, source, data):
        raise NotImplementedError()

    @abstractmethod
    def _copy_results(self, s, source, loader, stats):
        raise NotImplementedError()


class ActivityJournalCalculator(DataFrameCalculator):

    def __delimit_query(self, q):
        start, finish = self._start_finish(type=local_time_to_time)
        log.debug(f'Delimit times: {start} - {finish}')
        if start:
            q = q.filter(ActivityJournal.start >= start)
        if finish:
            q = q.filter(ActivityJournal.start <= finish)
        return q

    def _missing(self, s):
        existing_ids = s.query(Timestamp.key).filter(Timestamp.owner == self.owner_out)
        q = s.query(ActivityJournal.start). \
            filter(not_(ActivityJournal.id.in_(existing_ids.cte()))). \
            order_by(ActivityJournal.start)
        return [row[0] for row in self.__delimit_query(q)]

    def _delete(self, s):
        start, finish = self._start_finish(type=local_time_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner_out)
        activity_journals = self.__delimit_query(s.query(ActivityJournal.id))
        statistic_journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte()),
                   StatisticJournal.source_id.in_(activity_journals))
        for repeat in range(2):
            if repeat:
                s.query(StatisticJournal).filter(StatisticJournal.id.in_(statistic_journals.cte())). \
                    delete(synchronize_session=False)
                Timestamp.clean_keys(log, s,
                                     s.query(StatisticJournal.source_id).
                                     filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte())),
                                     self.owner_out, constraint=None)
            else:
                n = s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.id.in_(statistic_journals.cte())).scalar()
                if n:
                    log.warning(f'Deleting {n} statistics for {long_cls(self.owner_out)} from {start} to {finish}')
                else:
                    log.warning(f'No statistics to delete for {long_cls(self.owner_out)} from {start} to {finish}')
                    # log.debug(statistic_journals)
        s.commit()

    def _get_source(self, s, time):
        return s.query(ActivityJournal).filter(ActivityJournal.start == time).one()
