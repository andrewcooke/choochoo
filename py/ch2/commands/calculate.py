
from logging import getLogger

from .args import FORCE, LIKE, FINISH, START, WORKER, parse_pairs, KARG
from ..pipeline.pipeline import run_pipeline
from ..sql.tables.pipeline import PipelineType

log = getLogger(__name__)


def calculate(config):
    '''
## calculate

    > ch2 calculate

Calculate any missing statistics.

    > ch2 calculate --force [START [FINISH]]

Delete statistics in the date range (or all, if omitted) and then calculate new values.

    > ch2 --dev calculate --like '%Activity%' --force 2020-01-01 -Kn_cpu=1

Calculate activity statistics from 2020 onwards in a single process for debugging.
    '''
    args = config.args
    run_statistic_pipelines(config, force=args[FORCE], like=args[LIKE], start=args[START], finish=args[FINISH],
                            worker=args[WORKER], **parse_pairs(args[KARG]))


def run_statistic_pipelines(data, force=False, like=tuple(), start=None, finish=None, worker=None, **kargs):
    run_pipeline(data, PipelineType.CALCULATE, force=force, like=like, start=start, finish=finish, worker=worker,
                 **kargs)
