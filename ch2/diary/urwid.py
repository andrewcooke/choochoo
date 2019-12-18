
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


def create_value(model):
    text = [label(model[LABEL] + ': ')]
    if model[UNITS] == S:
        text += [format_seconds(model[VALUE])]
    elif model[UNITS] == W:
        text += [format_watts(model[VALUE])]
    elif model[UNITS] == M:
        text += [format_metres(model[VALUE])]
    elif model[UNITS] == PC:
        text += [format_percent(model[VALUE])]
    else:
        if isinstance(model[VALUE], float):
            if 1 < model[VALUE] < 1000:
                text += ['%.1f' % model[VALUE]]
            else:
                text += ['%g' % model[VALUE]]
        else:
            text += [str(model[VALUE])]
        if model[UNITS]:
            text += [model[UNITS]]
    if MEASURES in model:
        extras = [' ']
        for schedule in model[MEASURES][SCHEDULES]:
            percentile, rank = model[MEASURES][SCHEDULES][schedule]
            q = 1 + min(4, percentile / 20)
            extras.append(quintile(q, f'{int(percentile)}%:{rank}/{schedule} '))
        text += extras
    return Text(text)


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
        import pdb; pdb.set_trace()
        branch_columns = []
        for names in specs:
            try:
                columns, reduced_model = [], list(model)
                for name in names:
                    for i, m in enumerate(reduced_model):
                        if isinstance(m, list) and isinstance(m[0], dict) and m[0].get(LABEL, None) == name:
                            columns.append(m[0])
                            del reduced_model[i]
                            break
                    raise Exception(f'Missing column {name}')
                columns = [default_before(column, before, after, leaf) for column in columns]
                branch_columns.append(Columns(columns))
                model = reduced_model
            except Exception as e:
                log.warning(e)
        branch = [layout(m, before, after, leaf) for m in model]
        branch.extend(branch_columns)
        return branch

    return before


def default_before(model, before, after, leaf):
    if not isinstance(model, list):
        raise Exception(f'"before" called with non-list type ({type(model)}, {model})')
    return [layout(m, before, after, leaf) for m in model]

BEFORE = defaultdict(
    lambda: default_before,
    {'activity': columns(('Min Time', 'Med Time'),
                         ('Max Med Heart Rate', 'Max Mean Power Estimate'),
                         ('HR Zones', 'Climbs'))})


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
