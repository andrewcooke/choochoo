
import re
from logging import getLogger

'''
The model is intended to be, as far as reasonable, self-describing.
In other words, clients are expected to be able to display the model even if the order of the data changes,
or if entries are added or removed.
Exceptions to the above should be keyed on tag attributes (see below).
The 'low-level' details (eg attribute names) of the model should not change.

The model is hierarchical, modelled as a tree.
So the outermost list is the 'root' and each entry is a 'node'.
Non-leaf nodes, including  the root, are lists.
Leaf nodes are dicts / maps and represent individual 'values'.

Within a non-leaf node, the first child node is a 'text' type node (see below) that acts as a 'title' 
describing the contents of the node.

All leaf nodes have a 'type' attribute which describes the type of the node.
The contents of a node of a given type match the constructor functions below.
All leaf nodes have a 'value' attribute.
All leaf nodes have a 'tag' attribute that is intended as a machine-readable semantic marker (so where the client 
needs exceptional processing I will try to maintain these even if the text of a node changes, for example).
'''


COMPARE_LINKS = 'compare-links'

# diary and general
DB = 'db'
DP = 'dp'
EDIT = 'edit'
FLOAT = 'float'
HI = 'hi'
IMAGE = 'image'
INTEGER = 'integer'
LABEL = 'label'
LINK = 'link'
LO = 'lo'
MEASURES = 'measures'
TAG = 'tag'
SCHEDULES = 'schedules'
SCORE = 'score'
TEXT = 'text'
TYPE = 'type'
UNITS = 'units'
VALUE = 'value'


log = getLogger(__name__)


def from_field(topic_field, statistic_journal):
    kargs = dict(topic_field.model)
    type = kargs[TYPE]
    del kargs[TYPE]
    kargs.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.title,
                 db=statistic_journal)
    if statistic_journal.statistic_name.units:
        kargs.update(units=statistic_journal.statistic_name.units)
    return {SCORE: score, INTEGER: integer, FLOAT: float, EDIT: edit}[type](**kargs)


def to_tag(text):
    text = re.sub(r'\W+', '-', text)
    text = re.sub(r'-?(\w+(:?-\w+)*)-?', r'\1', text)
    return text.lower()


# --- mutable types

def score(label, value, db=None):
    if db is None: log.warning(f'No db for score {label}/{value}')
    return {TYPE: SCORE, LABEL: label, VALUE: value, DB: db}


def integer(label, value, units=None, lo=None, hi=None, db=None):
    if db is None: log.warning(f'No db for integer {label}/{value}')
    return {TYPE: INTEGER, LABEL: label, VALUE: value, UNITS: units, LO: lo, HI: hi, DB: db}


def float(label, value, units=None, lo=None, hi=None, dp=1, db=None):
    if db is None: log.warning(f'No db for float {label}/{value}')
    return {TYPE: FLOAT, LABEL: label, VALUE: value, UNITS: units, LO: lo, HI: hi, DP: dp, DB: db}


def edit(label, value, db=None):
    if db is None: log.warning(f'No db for edit {label}/{value}')
    return {TYPE: EDIT, LABEL: label, VALUE: value, DB: db}


# --- immutable types

def text(value, tag=None, db=None):
    text = {TYPE: TEXT, VALUE: value, TAG: to_tag(tag or value)}
    if db: text[DB] = db
    return text


def value(label, value, tag=None, units=None, measures=None):
    return {TYPE: VALUE, LABEL: label, VALUE: value, TAG: to_tag(tag or label), UNITS: units, MEASURES: measures}


def measures(schedules):
    # schedules are a map from schedule to (percent, rank) tuples
    return {TYPE: MEASURES, SCHEDULES: schedules}


def link(value, db=None, tag=None):
    if not isinstance(db, tuple): log.warning(f'Bad db for link {value}')
    return {TYPE: LINK, VALUE: value, TAG: to_tag(tag or value), DB: db}


def image(value, tag=None):
    return {TYPE: IMAGE, VALUE: value, TAG: to_tag(tag or value)}


# --- decorators

def optional_text(name, tag=None):
    def decorator(f):
        def decorated(*args, **kargs):
            first = True
            for value in f(*args, **kargs):
                if first:
                    yield text(name, tag=tag)
                    first = False
                yield value
        return decorated
    return decorator


def trim_no_stats(f):

    def decorated(*args, **kargs):
        result = list(f(*args, **kargs))

        def trim(model):
            if isinstance(model, list):
                head, rest = model[0:1], model[1:]
                rest = [x for x in [trim(entry) for entry in rest] if x]
                if rest:
                    return head + rest
                else:
                    return []
            else:
                return model
        return trim(result)

    return decorated
