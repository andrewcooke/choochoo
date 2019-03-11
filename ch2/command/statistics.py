
from .args import FORCE, LIKE, FINISH, START, WORKER
from ..squeal.tables.pipeline import PipelineType
from ..stoats.pipeline import run_pipeline


def statistics(args, log, db):
    '''
## statistics

    > ch2 statistics

Generate any missing statistics.

    > ch2 statistics --force [DATE]

Delete statistics after the date (or all, if omitted) and then generate new values.
    '''
    run_pipeline(log, db, PipelineType.STATISTIC,
                 force=args[FORCE], like=args[LIKE], start=args[START], finish=args[FINISH],
                 worker=args[WORKER] is not None, id=args[WORKER])
