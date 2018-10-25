
from ch2.command.args import DIR


def garmin(args, log, db):
    '''
# garmin

    ch2 garmin DIR

    '''
    dir = args.dir(DIR, rooted=False)
    with db.session_context() as s:
        pass