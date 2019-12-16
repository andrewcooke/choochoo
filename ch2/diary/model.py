from ch2.sql.types import short_cls, long_cls

DP = 'dp'
EDIT = 'edit'
FLOAT = 'float'
HI = 'hi'
HR_ZONES = 'hr_zones'
LABEL = 'label'
LINK = 'link'
LINKS = 'links'
LO = 'lo'
MEASURES = 'measures'
MENU = 'menu'
OWNER = 'owner'
PERCENT_TIMES = 'percent_times'
SCHEDULES = 'schedules'
SCORE0 = 'score0'
SCORE1 = 'score1'
TEXT = 'text'
TIME = 'time'
TYPE = 'type'
UNITS = 'units'
VALUE = 'value'


def from_field(topic_field, statistic_journal):
    # todo - type?
    model = dict(topic_field.model)
    model.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.name,
                 units=statistic_journal.statistic_name.units)
    return model


# todo - remove kargs?

def text(text, width=4, height=1, owner=None, **kargs):
    model = dict(kargs)
    model.update(type=TEXT, value=text, width=width, height=height)
    if owner: model.update(owner=long_cls(owner))
    return model


def value(label, value, units=None, measures=None, **kargs):
    model = dict(kargs)
    model.update(type=VALUE, label=label, value=value, units=units)
    if measures and measures[SCHEDULES]: model.update(measures=measures)
    return model


def link(label, value, **kargs):
    return dict(type=LINK, label=label, value=value, **kargs)


def hr_zones(zones, percent_times):
    return dict(type=HR_ZONES, hr_zones=zones, percent_times=percent_times)


def menu(label, links, **kargs):
    # links is list of link types
    return dict(type=MENU, label=label, links=links, **kargs)