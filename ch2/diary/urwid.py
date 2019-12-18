
from collections import defaultdict
from copy import copy
from logging import getLogger
from sys import argv

from urwid import Pile, Text, MainLoop, Filler, Divider, Edit, Columns

from ..data import session
from ..diary.model import TYPE, VALUE, TEXT, DP, HI, LO, FLOAT, UNITS, SCORE0, SCORE1, HR_ZONES, PERCENT_TIMES, \
    LABEL, EDIT, MEASURES, SCHEDULES, LINKS, MENU, TAG
from ..lib import to_date, format_seconds
from ..lib.utils import PALETTE_RAINBOW, format_watts, format_percent, format_metres
from ..stats.names import S, W, PC, M
from ..urwid.tui.decorators import Border, Indent
from ..urwid.tui.widgets import Float, Rating0, Rating1, ArrowMenu

log = getLogger(__name__)
HR_ZONES_WIDTH = 30


# for text markup
def em(text): return 'em', text
def error(text): return 'error', text
def label(text): return 'label', text
def zone(zone, text): return 'zone-%d' % zone, text
def quintile(quintile, text): return 'quintile-%d' % quintile, text


def build(model):
    log.debug(model)
    return Border(Filler(layout(model)))


def layout(model, before=None, after=None, leaf=None):
    '''
    Takes a model and returns an urwid widget.
    The model is nested lists, forming a tree, with nodes that are dicts.
    This function traverses the tree in a depth-first manner, converting dicts using leaf and assembling
    the visited nodes using after.
    The before map can be used to intercept normal processing.
    Before and after are keyed on the 'owner' or 'label' entry in the first dict in the list;
    leaf is keyed on the 'type' entry in the dict.
    '''

    before = before or BEFORE
    after = after or AFTER
    leaf = leaf or LEAF

    if isinstance(model, list):
        if not model:
            raise Exception('Empty list in model')
        if not isinstance(model[0], dict):
            raise Exception(f'Model list with no head element: {model}')
        key = model[0].get(TAG, None)
        try:
            branch = before[key](model, copy(before), copy(after), copy(leaf))
        except Exception as e:
            log.error(f'Error ({e}) while processing {model}')
            raise
        return after[key](branch)
    else:
        if not isinstance(model, dict):
            raise Exception(f'Model entry of type {type(model)} ({model})')
        key = model.get(TYPE, None)
        return leaf[key](model)


# todo - should just be values

def create_hr_zones(model, width=HR_ZONES_WIDTH):
    body = []
    for z, percent_time in zip(model[HR_ZONES], model[PERCENT_TIMES]):
        text = ('%d:' + ' ' * (width - 6) + '%3d%%') % (z, int(0.5 + percent_time))
        column = 100 / width
        left = int((percent_time + 0.5 * column) // column)
        text_left = text[0:left]
        text_right = text[left:]
        body.append(Text([zone(z, text_left), text_right]))
    return Pile(body)


def fmt_value_units(model):
    if model[UNITS] == S:
        return [format_seconds(model[VALUE])]
    elif model[UNITS] == W:
        return [format_watts(model[VALUE])]
    elif model[UNITS] == M:
        return [format_metres(model[VALUE])]
    elif model[UNITS] == PC:
        return [format_percent(model[VALUE])]
    else:
        text = []
        if isinstance(model[VALUE], float):
            if 1 < model[VALUE] < 1000:
                text += ['%.1f' % model[VALUE]]
            else:
                text += ['%g' % model[VALUE]]
        else:
            text += [str(model[VALUE])]
        if model[UNITS]:
            text += [model[UNITS]]
        return text


def fmt_value_measures(model):
    measures = []
    if MEASURES in model:
        for schedule in model[MEASURES][SCHEDULES]:
            percentile, rank = model[MEASURES][SCHEDULES][schedule]
            q = 1 + min(4, percentile / 20)
            measures.append(quintile(q, f'{int(percentile)}%:{rank}/{schedule} '))
    return measures


def create_value(model):
    return Text([label(model[LABEL] + ': ')] + fmt_value_units(model) + [' '] + fmt_value_measures(model))


def default_leaf(model):
    raise Exception(f'Unexpected leaf {model}')

LEAF = defaultdict(
    lambda: default_leaf,
    {
        TEXT: lambda model: Text(model[VALUE]),
        EDIT: lambda model: Edit(caption=label(model[LABEL] + ': '), edit_text=model[VALUE] or ''),
        FLOAT: lambda model: Float(caption=label(model[LABEL] + ': '), state=model[VALUE],
                                   minimum=model[LO], maximum=model[HI], dp=model[DP],
                                   units=model[UNITS]),
        SCORE0: lambda model: Rating0(caption=label(model[LABEL] + ': '), state=model[VALUE]),
        SCORE1: lambda model: Rating1(caption=label(model[LABEL] + ': '), state=model[VALUE]),
        HR_ZONES: create_hr_zones,
        VALUE: create_value,
        MENU: lambda model: ArrowMenu(label(model[LABEL] + ': '),
                                      {link[LABEL]: link[VALUE] for link in model[LINKS]})
    })


def columns(*specs):

    def before(model, before, after, leaf):
        branch_columns = []
        for names in specs:
            try:
                columns, reduced_model, found = [], list(model), False
                for name in names:
                    for i, m in enumerate(reduced_model):
                        if isinstance(m, list) and isinstance(m[0], dict) and m[0].get(TAG) == name:
                            columns.append(m)
                            del reduced_model[i]
                            found = True
                            break
                    if not found:
                        raise Exception(f'Missing column {name}')
                columns = [layout(column, before, after, leaf) for column in columns]
                branch_columns.append(Columns(columns))
                model = reduced_model
            except Exception as e:
                log.warning(e)
        branch = [layout(m, before, after, leaf) for m in model]
        branch.extend(branch_columns)
        return branch

    return before


def value_to_row(value, has_measures=None):
    # has_measures can be true/false to force
    row = [Text(label(value[LABEL])), Text(fmt_value_units(value))]
    if has_measures is True or MEASURES in value:
        row += [Text(fmt_value_measures(value))]
    elif has_measures is None:
        row += [Text('')]
    return row


def rows_to_table(rows):
    widths = [max(len(row.text) for row in column) for column in zip(*rows)]
    return Columns([(width+1, Pile(column)) for column, width in zip(zip(*rows), widths)])


def values_table(model, before, after, leaf):
    values = [m for m in model if isinstance(m, dict) and m.get(TYPE, None) == 'value']
    rest = [layout(m, before, after, leaf) for m in model if m not in values]
    table = rows_to_table([value_to_row(value) for value in values])
    return rest + [table]


def climbs_table(model, before, after, leaf):

    def climb(model):
        # assumes elevation, distance and time entries, in that order
        return [Text(fmt_value_units(model[0])), Text(fmt_value_units(model[1])), Text(fmt_value_units(model[2])),
                Text(fmt_value_measures(model[0]))]

    elevations = [m for m in model if isinstance(m, list) and m[0].get(LABEL, None) == 'Elevation']
    rest = [layout(m, before, after, leaf) for m in model if m not in elevations]
    table = rows_to_table([climb(elevation) for elevation in elevations])
    return rest + [table]


def table(name, value):

    def before(model, before, after, leaf):
        title = layout(model[0], before, after, leaf)
        has_measures = any(MEASURES in m for m in model[1:])
        headers = [name, value]
        if has_measures: headers.append('Stats')
        rows = [[Text(label(header)) for header in headers]] + [value_to_row(m, has_measures) for m in model[1:]]
        return [title, rows_to_table(rows)]

    return before


def default_before(model, before, after, leaf):
    if not isinstance(model, list):
        raise Exception(f'"before" called with non-list type ({type(model)}, {model})')
    return [layout(m, before, after, leaf) for m in model]

BEFORE = defaultdict(
    lambda: default_before,
    {'activity': columns(('hr-zones-time', 'climbs'),
                         ('min-time', 'med-time'),
                         ('max-med-heart-rate', 'max-mean-power-estimate')),
     'min-time': table('Dist', 'Time'),
     'med-time': table('Dist', 'Time'),
     'max-med-heart-rate': table('Time', 'HR'),
     'max-mean-power-estimate': table('Time', 'Power'),
     'activity-statistics': values_table,
     'climbs': climbs_table
     })


def default_after(branch):
    head, tail = branch[0], branch[1:]
    if tail:
        return Pile([head, Indent(Pile(tail))])
    else:
        return head

AFTER = defaultdict(lambda: default_after)





if __name__ == '__main__':

    from ch2.diary.database import read_daily

    if len(argv) != 2:
        raise Exception('Usage: python -m ch2.diary.urwid date')
    date = to_date(argv[1])
    s = session('--dev -v5')
    data = list(read_daily(s, date))
    log.debug(f'Read {data}')
    widget = build(data)
    log.debug(f'Built {widget}')
    MainLoop(widget, palette=PALETTE_RAINBOW).run()
