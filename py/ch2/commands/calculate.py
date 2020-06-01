
from logging import getLogger

from .args import FORCE, LIKE, FINISH, START, WORKER, parse_pairs, KARG, UNLIKE, BASE
from ..sql.tables.pipeline import PipelineType
from ..pipeline.pipeline import run_pipeline

log = getLogger(__name__)


def calculate(args, sys, db):
    '''
## calculate

    > ch2 calculate

Calculate any missing statistics.

    > ch2 calculate --force [START [FINISH]]

Delete statistics in the date range (or all, if omitted) and then calculate new values.
    '''
    run_statistic_pipelines(sys, db, args[BASE], force=args[FORCE], like=args[LIKE], unlike=args[UNLIKE],
                            start=args[START], finish=args[FINISH], worker=args[WORKER] is not None, id=args[WORKER],
                            **parse_pairs(args[KARG]))


def run_statistic_pipelines(sys, db, base, force=False, like=tuple(), unlike=tuple(), start=None, finish=None,
                            worker=False, id=None, **kargs):
    run_pipeline(sys, db, base, PipelineType.CALCULATE, force=force, like=like, unlike=unlike, start=start, finish=finish,
                 worker=worker, id=id, **kargs)
