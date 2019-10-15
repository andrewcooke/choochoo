
from logging import getLogger

from .args import FORCE, LIKE, FINISH, START, WORKER, parse_pairs, KARG
from ..squeal.tables.pipeline import PipelineType
from ..stoats.pipeline import run_pipeline

log = getLogger(__name__)


def statistics(args, db):
    '''
## statistics

    > ch2 statistics

Generate any missing statistics.

    > ch2 statistics --force [DATE]

Delete statistics after the date (or all, if omitted) and then generate new values.
    '''
    run_pipeline(db, PipelineType.STATISTIC,
                 force=args[FORCE], like=args[LIKE], start=args[START], finish=args[FINISH],
                 worker=args[WORKER] is not None, id=args[WORKER], **parse_pairs(args[KARG]))
