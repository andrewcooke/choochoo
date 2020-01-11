
from ..model import DB
from ...sql import StatisticJournal


def str_or_none(x):
    return x is None or isinstance(x, str)


def rewrite_db(model):
    if isinstance(model, list):
        return [rewrite_db(m) for m in model]
    else:
        if DB in model:
            db = model[DB]
            if isinstance(db, StatisticJournal):
                model[DB] = db.id
            else:  # links have tuples
                model[DB] = [x if str_or_none(x) else x.id for x in db]
        return model
