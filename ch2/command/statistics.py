
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
    force, like, start, finish, worker = args[FORCE], args[LIKE], args[START], args[FINISH], args[WORKER]
    run_pipeline(log, db, PipelineType.STATISTIC,
                 force=force, like=like, start=start, finish=finish, worker=worker, prog=args.prog)
