
DP = 'dp'
EDIT = 'edit'
FLOAT = 'float'
HI = 'hi'
HR_ZONES = 'hr_zones'
LABEL = 'label'
LO = 'lo'
MEASURES = 'measures'
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
    model = dict(topic_field.model)
    model.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.name,
                 units=statistic_journal.statistic_name.units)
    return model


def text(text, width=4, height=1, **kargs):
    model = dict(kargs)
    model.update(type=TEXT, value=text, width=width, height=height)
    return model


def value(label, value, units=None, measures=None, **kargs):
    model = dict(kargs)
    model.update(type=VALUE, label=label, value=value, units=units)
    if measures and measures[SCHEDULES]: model.update(measures=measures)
    return model


def hr_zones(zones, percent_times):
    return dict(type=HR_ZONES, hr_zones=zones, percent_times=percent_times)
