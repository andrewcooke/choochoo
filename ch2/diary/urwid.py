from collections import defaultdict
from copy import copy
from logging import getLogger
from sys import argv

from urwid import Pile, Text, MainLoop, Filler, Divider, Edit, Columns

from ..data import session
from ..diary.model import TYPE, VALUE, TEXT, DP, HI, LO, FLOAT, UNITS, SCORE0, SCORE1, HR_ZONES, PERCENT_TIMES, \
    LABEL, EDIT, MEASURES, SCHEDULES, LINKS, MENU
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


def extend(dict, **kargs):
    dict = copy(dict)
    dict.update(**kargs)
    return dict


def build(model):
    log.debug(model)
#    return Border(Filler(stack_and_nest(list(collect_small_widgets(create_widgets(data))))))
    return Border(Filler(layout(model,)))


def layout(model, path=None, before=None, after=None, leaf=None):
    '''
    Takes a model and returns an urwid widget.
    The model is nested lists, forming a tree, with nodes that are dicts.
    This function traverses the tree in a depth-first manner, converting dicts using leaf and assembling
    the visited nodes using after.
    The before map can be used to intercept normal processing.
    Before and after are keyed on the 'value' entry in teh first dict in the list;
    leaf is keyed on the 'type' entry in the dict.
    '''

    path = path or []
    before = before or BEFORE
    after = after or AFTER
    leaf = leaf or LEAF

    if isinstance(model, list):
        key = model[0].get(VALUE, None) if model and isinstance(model[0], dict) else None
        branch = before[key](model, path + [key], copy(before), copy(after), copy(leaf))
        return after[key](path + [key], branch)
    else:
        key = model.get(TYPE, None)
        return leaf[key](path + [key], model)


def default_before(model, path, before, after, leaf):
    return [layout(m, path, before, after, leaf) for m in model]

BEFORE = defaultdict(lambda: default_before)


def default_after(path, branch):
    branch = Pile(branch)
    if len(path) > 1: branch = Indent(branch)
    return branch

AFTER = defaultdict(lambda: default_after)


def create_hr_zones(path, model, width=HR_ZONES_WIDTH):
    body = []
    for z, percent_time in zip(model[HR_ZONES], model[PERCENT_TIMES]):
        text = ('%d:' + ' ' * (width - 6) + '%3d%%') % (z, int(0.5 + percent_time))
        column = 100 / width
        left = int((percent_time + 0.5 * column) // column)
        text_left = text[0:left]
        text_right = text[left:]
        body.append(Text([zone(z, text_left), text_right]))
    return Pile(body)


def create_value(path, model):
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


def default_leaf(path, model):
    raise Exception(f'Unexpected leaf at {".".join([p if p else "" for p in path])}')

LEAF = defaultdict(
    lambda: default_leaf,
    {
        TEXT: lambda path, model: Text(model[VALUE]),
        EDIT: lambda path, model: Edit(caption=label(model[LABEL] + ': '), edit_text=model[VALUE] or ''),
        FLOAT: lambda path, model: Float(caption=label(model[LABEL] + ': '), state=model[VALUE],
                                         minimum=model[LO], maximum=model[HI], dp=model[DP],
                                         units=model[UNITS]),
        SCORE0: lambda path, model: Rating0(caption=label(model[LABEL] + ': '), state=model[VALUE]),
        SCORE1: lambda path, model: Rating1(caption=label(model[LABEL] + ': '), state=model[VALUE]),
        HR_ZONES: create_hr_zones,
        VALUE: create_value,
        MENU: lambda path, model: ArrowMenu(label(model[LABEL]), {link[LABEL]: link[VALUE] for link in model[LINKS]})
    })






def stack_and_nest(model, depth=0):
    if isinstance(model, list):
        widgets = [stack_and_nest(widget, depth=depth+1) for widget in model]
        if depth == 1: widgets = [Divider()] + widgets
        widgets = Pile(widgets)
        if depth: widgets = Indent(widgets)
        return widgets
    else:
        return model


def widget_size(widget, max_cols=4):
    for cls in (Float, Rating0, Rating1):
        if isinstance(widget, cls): return 1
    if isinstance(widget, Text) and not isinstance(widget, Edit):
        return min(max_cols, 1 + len(widget.text) // 13)
    return max_cols


def collect_small_widgets(widget, max_cols=4):
    if isinstance(widget, list):
        group, cols = [], 0
        for w in widget:
            if isinstance(w, list):
                if group:
                    if cols < max_cols:
                        group.append(('weight', max_cols - cols, Text('')))
                    yield Columns(group)
                    group, cols = [], 0
                yield list(collect_small_widgets(w, max_cols=max_cols))
            else:
                size = widget_size(w, max_cols=max_cols)
                if cols + size > max_cols:
                    if group:
                        if cols < max_cols:
                            group.append(('weight', max_cols - cols, Text('')))
                        yield Columns(group)
                    group, cols = [w], size
                else:
                    group.append(('weight', size, w))
                    cols += size
        if group:
            if cols < max_cols:
                group.append(('weight', max_cols - cols, Text('')))
            yield Columns(group)
    else:
        yield widget


def create_widgets(model):
    if isinstance(model, list):
        return [create_widgets(m) for m in model]
    else:
        type = model[TYPE]
        if type == TEXT:
            return Text(model[VALUE])
        elif type == EDIT:
            return Edit(caption=label(model[LABEL] + ': '), edit_text=model[VALUE] or '')
        elif type == FLOAT:
            return Float(caption=label(model[LABEL] + ': '), state=model[VALUE],
                         minimum=model[LO], maximum=model[HI], dp=model[DP], units=model[UNITS])
        elif type == SCORE0:
            return Rating0(caption=label(model[LABEL] + ': '), state=model[VALUE])
        elif type == SCORE1:
            return Rating1(caption=label(model[LABEL] + ': '), state=model[VALUE])
        elif type == HR_ZONES:
            return create_hr_zones(model)
        elif type == VALUE:
            return create_value(model)
        else:
            raise Exception(f'Unexpected model type: {type} ({model})')





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
