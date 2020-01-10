
from ..model import DB


def str_or_none(x):
    return x is None or isinstance(x, str)


def iterable(x):
    return isinstance(x, tuple) or isinstance(x, list)


def rewrite_db(model):
    if isinstance(model, list):
        return [rewrite_db(m) for m in model]
    else:
        if DB in model:
            db = model[DB]
            if not (str_or_none(db) or iterable(db) and all(str_or_none(x) for x in db)):
                if isinstance(db, tuple) or isinstance(db, list):
                    db = [x if str_or_none(x) else x.id for x in db]
                else:
                    db = db.id
                model[DB] = db
        return model
