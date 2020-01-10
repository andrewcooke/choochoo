
from ..model import DB


def rewrite_db(model):
    if isinstance(model, list):
        return [rewrite_db(m) for m in model]
    else:
        if DB in model:
            try:
                model[DB] = (x.id if x is not None else x for x in model[DB])
            except:
                model[DB] = model[DB].id
        return model
