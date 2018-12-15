
from re import sub

from .args import LABEL, LATITUDE, LONGITUDE, WIDTH, HEIGHT, ACTIVITY_GROUP, BORDER, START, FINISH, FORCE
from ..stoats.calculate.nearby import NearbySimilarityCalculator


def nearby_stats(args, log, db):
    '''
## nearby_stats

    > ch2 nearby_stats LABEL

Calculate the similarity matrix for nearby routes.
It will be saved in the database under the given LABEL.
    '''
    kargs = {}
    for name in START, FINISH, LABEL, LATITUDE, LONGITUDE, WIDTH, HEIGHT, ACTIVITY_GROUP, BORDER:
        if name in args and args[name] is not None:
            kargs[sub(r'-', '_', name)] = args[name]
    pipeline = NearbySimilarityCalculator(log, db, **kargs)
    pipeline.run(force=args[FORCE])
