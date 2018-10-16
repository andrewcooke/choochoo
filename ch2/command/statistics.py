
from .args import DATE, FORCE, mm
from ..stoats.calculate import run_statistics


def statistics(args, log, db):
    '''
# statistics

    ch2 statistics

Generate any missing statistics.

    ch2 statistics --force [date]

Delete statistics after the date (or all, if omitted) and then generate new values.
    '''
    force, date = args[FORCE], args[DATE]
    if date and not force:
        raise Exception('Only give a date when using %s' % mm(FORCE))
    run_statistics(log, db, force=force, after=date)
