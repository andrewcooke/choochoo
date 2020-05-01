
from collections import defaultdict
from copy import copy
from logging import getLogger
from re import compile, sub

from urwid import Pile, Text, Filler, Edit, Columns, Frame, Divider, Padding, connect_signal

from ...data.names import S, W, PC
from ...diary.model import TYPE, VALUE, TEXT, DP, HI, LO, FLOAT, UNITS, SCORE, LABEL, EDIT, MEASURES, SCHEDULES, TAG, \
    LINK, INTEGER, DB, value, text, COMPARE_LINKS
from ...lib import format_seconds
from ...lib.utils import format_watts, format_percent
from ...pipeline.display.activity.nearby import NEARBY_LINKS
from ...urwid.tui.decorators import Border, Indent
from ...urwid.tui.fixed import Fixed
from ...urwid.tui.tabs import Tab
from ...urwid.tui.widgets import Float, Rating0, Rating1, ArrowMenu, DividedPile, SquareButton, Integer

log = getLogger(__name__)

HR_ZONES_WIDTH = 32  # characters total

COLUMN_WIDTH = 6     # characters per column
N_COLUMNS = 12       # columns on screen (typically use multiple; 12 allows 3 or 4 'real' columns)


# for text markup
def em(text): return 'em', text
def error(text): return 'error', text
def label(text): return 'label', text
def zone(zone, text): return 'zone-%d' % zone, text
def quintile(quintile, text): return 'quintile-%d' % quintile, text


def build(model, f, layout):
    footer = ['meta-', em('q'), 'uit/e', em('x'), 'it/', em('s'), 'ave']
    footer += [' [shift]meta-']
    for sep, c in enumerate('dwmya'):
        if sep: footer += ['/']
        footer += [em(c)]
    footer += ['ctivity/', em('t'), 'oday']
    active = defaultdict(list)
    branch = layout(model, f, active)
    return active, Border(Frame(Filler(branch, valign='top'),
                                footer=Pile([Divider(), Text(footer, align='center')])))


def apply_before(model, f, active, before, after, leaf):
    key = model[0].get(TAG, None)
    return before[key](key, model, f, active, copy(before), copy(after), copy(leaf))


def layout(model, f, active, before, after, leaf):
    '''
    Takes a model and returns an urwid widget.
    The model is nested lists, forming a tree, with nodes that are dicts.
    This function traverses the tree in a depth-first manner, converting dicts using leaf and assembling
    the visited nodes using after.
    The before map can be used to intercept normal processing.
    Before and after are keyed on the 'tag' entry in the first dict in the list;
    leaf is keyed on the 'type' entry in the dict.
    '''

    if isinstance(model, list):
        if not model:
            raise Exception('Empty list in model')
        if not isinstance(model[0], dict):
            raise Exception(f'Model list with no head element: {model}')
        try:
            key, branch = apply_before(model, f, active, before, after, leaf)
            return after[key](branch)
        except Exception as e:
            log.error(f'Error ({e}) while processing {model}')
            raise
    else:
        if not isinstance(model, dict):
            raise Exception(f'Model entry of type {type(model)} ({model})')
        key = model.get(TYPE, None)
        try:
            return leaf[key](model, f, active)
        except Exception as e:
            log.error(f'Error ({e}) while processing leaf {key} in {model}')
            raise


def fmt_value_units(model):
    if model[UNITS] == S:
        return [format_seconds(model[VALUE])]
    elif model[UNITS] == W:
        return [format_watts(model[VALUE])]
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
    if MEASURES in model and model[MEASURES]:
        for schedule in model[MEASURES][SCHEDULES]:
            percentile, rank = model[MEASURES][SCHEDULES][schedule]
            q = 1 + min(4, percentile / 20)
            measures.append(quintile(q, f'{int(percentile)}%:{rank}/{schedule} '))
    if not measures:
        measures = [label('--')]
    return measures


def create_value(model, f, active):
    return Text([label(model[LABEL] + ': ')] + fmt_value_units(model) + [' '] + fmt_value_measures(model))


def create_value_no_measures(model, f, active):
    return Text([label(model[LABEL] + ': ')] + fmt_value_units(model))


def create_link(model, f, active):
    button = SquareButton(model[VALUE], state=model[DB])
    active[model[TAG]].append(button)
    return f(Padding(Fixed(button, len(model[VALUE]) + 2), width='clip'))


def wire(model, widget):
    def callback(w, v):
        model[DB].value = v
    connect_signal(widget, 'change', callback)
    return widget


def null_leaf(model, f, active):
    return model


def default_leaf(model, f, active):
    raise Exception(f'Unexpected leaf: {model}')


LEAF_DATE = defaultdict(
    lambda: default_leaf,
    {
        TEXT: lambda model, f, active: Text(model[VALUE]),
        EDIT: lambda model, f, active: f(wire(model,
                                              Edit(caption=label(model[LABEL] + ': '), edit_text=model[VALUE] or ''))),
        FLOAT: lambda model, f, active: f(wire(model,
                                               Float(caption=label(model[LABEL] + ': '), state=model[VALUE],
                                                     minimum=model[LO], maximum=model[HI], dp=model[DP],
                                                     units=model[UNITS]))),
        INTEGER: lambda model, f, active: f(wire(model,
                                                 Integer(caption=label(model[LABEL] + ': '), state=model[VALUE],
                                                         minimum=model[LO], maximum=model[HI], units=model[UNITS]))),
        SCORE: lambda model, f, active:  f(wire(model,
                                                Rating0(caption=label(model[LABEL] + ': '), state=model[VALUE]))),
        VALUE: create_value,
        LINK: create_link
    })


LEAF_SCHEDULE = defaultdict(
    lambda: default_leaf,
    {
        TEXT: lambda model, f, active: Text(model[VALUE]),
        VALUE: null_leaf,
        LINK: create_link
    })


def menu(key, model, f, active, before, after, leaf):
    menu = ArrowMenu(label(model[0][VALUE] + ': '),
                     {link[DB]: link[VALUE] for link in model[1:]})
    active[key].append(menu)
    return key, f(menu)


def side_by_side(*specs):

    def before(key, model, f, active, before, after, leaf):
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
                columns = [layout(column, f, active, before, after, leaf) for column in columns]
                branch_columns.append(Columns(columns))
                model = reduced_model
            except Exception as e:
                log.warning(e)
        branch = [layout(m, f, active, before, after, leaf) for m in model]
        branch.extend(branch_columns)
        return key, branch

    return before


def value_to_row(value, has_measures=None):
    # has_measures can be true/false to force
    row = [Text(label(value[LABEL])), Text(fmt_value_units(value))]
    if has_measures is True or (MEASURES in value and SCHEDULES in value[MEASURES] and value[MEASURES][SCHEDULES]):
        row += [Text(fmt_value_measures(value))]
    elif has_measures is None:
        row += [Text('')]
    return row


def rows_to_table(rows):
    widths = [max(len(row.text) for row in column) for column in zip(*rows)]
    return Columns([(width+1, Pile(column)) for column, width in zip(zip(*rows), widths)])


def values_table(key, model, f, active, before, after, leaf):
    values = [m for m in model if isinstance(m, dict) and m.get(TYPE, None) == 'value']
    rest = [layout(m, f, active, before, after, leaf) for m in model if m not in values]
    table = rows_to_table([value_to_row(value) for value in values])
    return key, rest + [table]


def climbs_table(key, model, f, active, before, after, leaf):

    def climb(model):
        # assumes title, elevation, distance and time entries, in that order
        return [Text(fmt_value_units(model[1])), Text(fmt_value_units(model[2])), Text(fmt_value_units(model[3])),
                Text(fmt_value_measures(model[1]))]

    elevations = [m for m in model if isinstance(m, list) and m[0].get(TAG, None) == 'climb']
    rest = [layout(m, f, active, before, after, leaf) for m in model if m not in elevations]
    table = rows_to_table([climb(elevation) for elevation in elevations])
    return key, rest[:1] + [table] + rest[1:]  # title, table, total


def table(name, value):

    def before(key, model, f, active, before, after, leaf):
        title = layout(model[0], f, active, before, after, leaf)
        has_measures = any(MEASURES in m for m in model[1:])
        headers = [name, value]
        if has_measures: headers.append('Stats')
        rows = [[Text(label(header)) for header in headers]] + [value_to_row(m, has_measures) for m in model[1:]]
        return key, [title, rows_to_table(rows)]

    return before


def shrimp_table(key, model, f, active, before, after, leaf):

    def reformat(model):
        branch = [Text(label(model[0][VALUE])), Text(str(model[1][VALUE])), Text(em(model[3][VALUE])),
                  Text(str(model[2][VALUE]))]
        for ranges in model[4:]:
            branch.append(Text(label(f'{ranges[1][VALUE]}-{ranges[2][VALUE]}/{ranges[0][TAG]}')))
        return branch

    return key, [Text(model[0][VALUE]), rows_to_table([reformat(m) for m in model[1:]])]


def collapse_title(key, model, f, active, before, after, leaf):
    def is_text(x):
        return isinstance(x, dict) and x[TYPE] == TEXT
    if len(model) == 2 and is_text(model[0]) and len(model[1]) and is_text(model[1][0]):
        model[1][0][VALUE] = f'{model[0][VALUE]} - {model[1][0][VALUE]}'
        model = model[1]
    else:
        del before[key]
    return apply_before(model, f, active, before, after, leaf)


def hr_zone(key, model, f, active, before, after, leaf):
    width = HR_ZONES_WIDTH
    z = model[0][VALUE]
    pc = model[1][VALUE]
    text = ('%d:' + ' ' * (width - 6) + '%3d%%') % (z, int(0.5 + pc))
    column = 100 / width
    left = int((pc + 0.5 * column) // column)
    text_left = text[0:left]
    text_right = text[left:]
    return key, Text([zone(z, text_left), text_right])


def schedule_combine(*patterns):

    patterns = [compile(pattern) for pattern in patterns]

    def before(key, model, f, active, before, after, leaf):

        def rows():
            current_pattern, columns = None, []
            for row in model:
                if not is_row(row):
                    yield row
                else:
                    if not current_pattern:
                        for pattern in patterns:
                            title = row[0][VALUE]
                            match = pattern.match(title)
                            if match:
                                current_pattern = pattern
                                i = title.find(match.group(1))
                                title = sub(r'\s+', ' ', title[:i] + title[(i + len(match.group(1))):])
                                columns = [text(title)]
                    if current_pattern:
                        match = current_pattern.match(row[0][VALUE])
                        if match:
                            columns.append(value(match.group(1), row[1][VALUE], units=row[1][UNITS]))
                        else:
                            yield columns
                            current_pattern, columns = None, []
                    else:
                        yield row
            if columns:
                yield columns

        if len(model) > 1 and any(is_row(b) for b in model[1:]):
            model = list(rows())
        return key, [layout(m, f, active, before, after, leaf) for m in model]

    return before


def drop_measures(key, model, f, active, before, after, leaf):
    leaf[VALUE] = create_value_no_measures
    return default_before(key, model, f, active, before, after, leaf)


def default_before(key, model, f, active, before, after, leaf):
    if not isinstance(model, list):
        raise Exception(f'"before" called with non-list type ({type(model)}, {model})')
    return key, [layout(m, f, active, before, after, leaf) for m in model]


BEFORE_DATE = defaultdict(
    lambda: default_before,
    {'activity': side_by_side(('hr-zones-time', 'climbs'),
                              ('min-time', 'med-time'),
                              ('max-med-heart-rate', 'max-mean-power-estimate')),
     'min-time': table('Dist', 'Time'),
     'med-time': table('Dist', 'Time'),
     'max-med-heart-rate': table('Time', 'HR'),
     'max-mean-power-estimate': table('Time', 'Power'),
     'activity-statistics': values_table,
     'segments': collapse_title,
     'segment': values_table,
     'climbs': climbs_table,
     'shrimp': shrimp_table,
     'nearbys': collapse_title,
     'hr-zone': hr_zone,
     'database': drop_measures,
     NEARBY_LINKS: menu,
     COMPARE_LINKS: menu
     })


BEFORE_SCHEDULE = defaultdict(
    lambda: schedule_combine(r'Min (\d+km) Time', r'Med (\d+km) Time', r'Max Med HR (\d+m)'),
    {})


def widget_size(widget, max_cols=N_COLUMNS):
    if isinstance(widget, Tab): widget = widget.w
    for cls in (Float, Rating0, Rating1):
        if isinstance(widget, cls): return 3
    if isinstance(widget, ArrowMenu): return 6
    if isinstance(widget, Text) and not isinstance(widget, Edit):
        return min(max_cols, 1 + len(widget.text) // COLUMN_WIDTH)
    return max_cols


def pack_widgets(branch, max_cols=N_COLUMNS):
    new_branch = [branch[0]]
    columns, width = [], 0
    for widget in branch[1:]:
        size = widget_size(widget)
        if size + width <= max_cols:
            columns.append((COLUMN_WIDTH * size, widget))
            width += size
        else:
            if columns:
                new_branch.append(Columns(columns))
            columns, width = [(COLUMN_WIDTH * size, widget)], size
    if columns:
        new_branch.append(Columns(columns))
    return default_after(new_branch)


def title_after(branch):
    head, tail = branch[0], branch[1:]
    if tail:
        return Pile([head, Divider(), Indent(DividedPile(tail))])
    else:
        return head


def null_after(branch):
    return branch


def is_row(branch):
    # check for row in schedule format
    return isinstance(branch, list) and len(branch) > 1 and isinstance(branch[1], dict) and branch[1][TYPE] == VALUE


def schedule_tables(branch):

    def fmt_rows(branch, ncols, max_cols=4):
        row = [branch[0]]
        for b in branch[1:]:
            # extra case to handle up/down arrow in fitness
            row.append(create_value_no_measures(b, None, None) if isinstance(b, dict) else b)
            if len(row) == max_cols:
                yield row
                row = [Text('')]
        if len(row) > 1:
            while len(row) < max_cols: row.append(Text(''))
            yield row

    if is_row(branch):
        return branch  # will be processed below
    if isinstance(branch, list) and len(branch) > 1 and any(is_row(b) for b in branch[1:]):
        ncols = max(len(b) for b in branch[1:] if is_row(b))
        all_rows, table = [], []
        for b in branch[1:]:
            if is_row(b):
                for row in fmt_rows(b, ncols): table.append(row)
            else:
                if table:
                    all_rows.append(Columns([Pile(col) for col in zip(*table)]))
                    table = []
                all_rows.append(b)
        if table:
            all_rows.append(Columns([Pile(col) for col in zip(*table)]))
        return Pile([branch[0], Indent(Pile(all_rows))])
    else:
        return default_after(branch)


def default_after(branch):
    head, tail = branch[0], branch[1:]
    if tail:
        return Pile([head, Indent(Pile(tail))])
    else:
        return head


AFTER_DATE = defaultdict(
    lambda: default_after,
    {'status': pack_widgets,
     'nearby': pack_widgets,
     'title': title_after,
     'hr-zone': null_after,
     NEARBY_LINKS: null_after,
     COMPARE_LINKS: null_after})


AFTER_SCHEDULE = defaultdict(
    lambda: schedule_tables,
    {'title': title_after})


def layout_date(model, f, active, before=BEFORE_DATE, after=AFTER_DATE, leaf=LEAF_DATE):
    return layout(model, f, active, before=before, after=after, leaf=leaf)


def layout_schedule(model, f, active, before=BEFORE_SCHEDULE, after=AFTER_SCHEDULE, leaf=LEAF_SCHEDULE):
    return layout(model, f, active, before=before, after=after, leaf=leaf)
