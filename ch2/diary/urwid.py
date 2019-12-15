
from logging import getLogger
from sys import argv

from urwid import Pile, Text, MainLoop, Filler, Divider, Edit, Columns

from ..data import session
from ..diary.model import TYPE, VALUE, TEXT, DP, HI, LO, FLOAT, UNITS, SCORE0, SCORE1, HR_ZONES, PERCENT_TIMES, \
    LABEL, EDIT, MEASURES, SCHEDULES
from ..lib import to_date, format_seconds
from ..lib.utils import PALETTE_RAINBOW, format_watts, format_percent, format_metres
from ..stats.names import S, W, PC, M
from ..urwid.tui.decorators import Border, Indent
from ..urwid.tui.widgets import Float, Rating0, Rating1

log = getLogger(__name__)
HR_ZONES_WIDTH = 30



def em(text): return 'em', text

def error(text): return 'error', text

def label(text): return 'label', text

def zone(zone, text): return ('zone-%d' % zone, text)

def quintile(quintile, text): return ('quintile-%d' % quintile, text)


def build(data):
    return Border(Filler(stack_and_nest(list(collect_small_widgets(create_widgets(data))))))


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
