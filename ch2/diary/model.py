
import re
from logging import getLogger


DB = 'db'
DP = 'dp'
EDIT = 'edit'
FLOAT = 'float'
HI = 'hi'
INTEGER = 'integer'
LABEL = 'label'
LINK = 'link'
LO = 'lo'
MEASURES = 'measures'
TAG = 'tag'
SCHEDULES = 'schedules'
SCORE = 'score'
TEXT = 'text'
TIME = 'time'
TYPE = 'type'
UNITS = 'units'
VALUE = 'value'

log = getLogger(__name__)


def from_field(topic_field, statistic_journal):
    kargs = dict(topic_field.model)
    type = kargs[TYPE]
    del kargs[TYPE]
    kargs.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.name,
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

def text(value, tag=None):
    return {TYPE: TEXT, VALUE: value, TAG: to_tag(tag or value)}


def value(label, value, tag=None, units=None, measures=None):
    return {TYPE: VALUE, LABEL: label, VALUE: value, TAG: to_tag(tag or label), UNITS: units, MEASURES: measures}


def measures(schedules):
    # schedules are a map from schedule to (percent, rank) tuples
    return {TYPE: MEASURES, SCHEDULES: schedules}


def link(value, tag=None, db=None):
    if db is None: log.warning(f'No db for link {value}')
    return {TYPE: LINK, VALUE: value, TAG: to_tag(tag or value), DB: db}


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
