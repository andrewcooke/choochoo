
import re

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
SCORE0 = 'score0'
TEXT = 'text'
TIME = 'time'
TYPE = 'type'
UNITS = 'units'
VALUE = 'value'


def from_field(topic_field, statistic_journal):
    kargs = dict(topic_field.model)
    type = kargs[TYPE]
    del kargs[TYPE]
    kargs.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.name)
    if statistic_journal.statistic_name.units:
        kargs.update(units=statistic_journal.statistic_name.units)
    return {SCORE0: score0, INTEGER: integer, FLOAT: float, EDIT: edit}[type](**kargs)


def to_tag(text):
    text = re.sub(r'\W+', '-', text)
    text = re.sub(r'-?(\w+(:?-\w+)*)-?', r'\1', text)
    return text.lower()


# --- mutable types

def score0(label, value):
    return {TYPE: SCORE0, LABEL: label, VALUE: value}


def integer(label, value, units=None, lo=None, hi=None):
    return {TYPE: FLOAT, LABEL: label, VALUE: value, UNITS: units, LO: lo, HI: hi}


def float(label, value, units=None, lo=None, hi=None, dp=1):
    return {TYPE: FLOAT, LABEL: label, VALUE: value, UNITS: units, LO: lo, HI: hi, DP: dp}


def edit(label, value):
    return {TYPE: EDIT, LABEL: label, VALUE: value}


# --- immutable types

def text(text, tag=None):
    return {TYPE: TEXT, VALUE: text, TAG: to_tag(tag or text)}


def value(label, value, tag=None, units=None, measures=None):
    return {TYPE: VALUE, LABEL: label, VALUE: value, TAG: to_tag(tag or label), UNITS: units, MEASURES: measures}


def measures(schedules):
    # schedules are a map from schedule to (percent, rank) tuples
    return {TYPE: MEASURES, SCHEDULES: schedules}


def link(label, value, tag=None):
    return {TYPE: LINK, LABEL: label, VALUE: value, TAG: to_tag(tag or label)}


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
