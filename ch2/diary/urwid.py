
from logging import getLogger
from sys import argv

from urwid import Pile, Text, MainLoop, Filler, Divider, Edit, Columns

from ch2.diary.model import TYPE, LABEL, VALUE, TEXT, DP, HI, LO, FLOAT, UNITS, SCORE0, SCORE1
from ch2.urwid.tui.widgets import Float, Rating0, Rating1
from ..data import session
from ..lib import to_date
from ..lib.utils import PALETTE_RAINBOW
from ..urwid.tui.decorators import Border, Indent

log = getLogger(__name__)


def build(data):
    return Border(Filler(stack_and_nest(collect_small_fields(create_widgets(data)))))


def stack_and_nest(model, depth=0):
    log.debug(f'Stacking {model}')
    if isinstance(model, list):
        widgets = [stack_and_nest(widget, depth=depth+1) for widget in model]
        if depth == 1: widgets = [Divider()] + widgets
        widgets = Pile(widgets)
        if depth: widgets = Indent(widgets)
        return widgets
    else:
        return model


def collect_small_fields(model, max_cols=4):

    def group(models):
        group = []
        for model in models:
            if len(group) == max_cols or (
                    isinstance(model, list) or isinstance(model, Text) or isinstance(model, Edit)):
                if group:
                    yield Columns(group)
                    group = []
                yield model
            else:
                group.append(model)
        if group:
            yield group

    if isinstance(model, list):
        return list(group([collect_small_fields(m) for m in model]))
    else:
        return model


def create_widgets(model):
    log.debug(f'Converting {model}')
    if isinstance(model, list):
        return [create_widgets(m) for m in model]
    else:
        type = model[TYPE]
        if type == LABEL:
            return Text(model[VALUE])
        elif type == TEXT:
            return Edit(caption=model[LABEL] + ': ', edit_text=model[VALUE] or '')
        elif type == FLOAT:
            return Float(caption=model[LABEL] + ': ', state=model[VALUE],
                         minimum=model[LO], maximum=model[HI], dp=model[DP], units=model[UNITS])
        elif type == SCORE0:
            return Rating0(caption=model[LABEL] + ': ', state=model[VALUE])
        elif type == SCORE1:
            return Rating1(caption=model[LABEL] + ': ', state=model[VALUE])
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
