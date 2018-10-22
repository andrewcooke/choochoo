
from .args import DATE, FORCE, mm, LIKE
from ..squeal.tables.pipeline import PipelineType
from ..stoats.calculate import run_pipeline_after


def statistics(args, log, db):
    '''
# statistics

    ch2 statistics

Generate any missing statistics.

    ch2 statistics --force [date]

Delete statistics after the date (or all, if omitted) and then generate new values.
    '''
    force, date, like = args[FORCE], args[DATE], args[LIKE]
    if date and not force:
        raise Exception('Only give a date when using %s' % mm(FORCE))
    run_pipeline_after(log, db, PipelineType.STATISTIC, after=date, force=force, like=like)
