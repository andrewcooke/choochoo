
from logging import getLogger

from .args import LIKE, WORKER, ARG, parse_pairs, KARG
from ..pipeline.mproc import run_pipeline
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
    run_pipeline(config, PipelineType.PROCESS, *args[ARG],
                 like=args[LIKE], worker=args[WORKER], **parse_pairs(args[KARG]))
