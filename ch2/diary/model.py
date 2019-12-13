
DP = 'dp'
FLOAT = 'float'
HI = 'hi'
LABEL = 'label'  # constant
LO = 'lo'
TEXT = 'text'    # editable
TYPE = 'type'
UNITS = 'units'
VALUE = 'value'
SCORE0 = 'score0'
SCORE1 = 'score1'


def from_field(topic_field, statistic_journal):
    model = dict(topic_field.model)
    model.update(value=statistic_journal.value,
                 label=statistic_journal.statistic_name.name,
                 units=statistic_journal.statistic_name.units)
    return model


def label(text, **kargs):
    model = dict(kargs)
    model.update(type=LABEL, value=text)
    return model
