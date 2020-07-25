
from logging import getLogger

from .args import LIKE, WORKER, ARG, parse_pairs, KARG, FORCE, CPROFILE
from ..common.args import mm
from ..pipeline.process import run_pipeline
from ..sql.tables.pipeline import PipelineType

log = getLogger(__name__)


def process(config):
    '''
## process

    > ch2 process

Update the database, reading news files and calculating missing statistics.

    > ch2 process --force

Delete statistics and then calculate new values.

    > ch2 --dev calculate --like '%Activity%' --force 2020-01-01 -Kn_cpu=1

Calculate activity statistics from 2020 onwards in a single process for debugging.
    '''
    args = config.args
    if bool(args[WORKER]) != bool(args[ARG]):
        raise Exception(f'{mm(WORKER)} and arguments should be used together')
    if args[LIKE] and args[WORKER]:
        raise Exception(f'{mm(FORCE)} and {mm(LIKE)} cannot be used with {mm(WORKER)}')
    run_pipeline(config, PipelineType.PROCESS, *args[ARG],
                 like=args[LIKE], worker=args[WORKER], force=args[FORCE], cprofile=args[CPROFILE],
                 **parse_pairs(args[KARG]))
