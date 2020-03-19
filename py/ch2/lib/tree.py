

def to_tree(model, format, children):
    '''
    this will yield lines formatted as a tree.

    model is the data to be displayed (for example, nested dicts).

    format is a function that takes the current model and returns a label plus an optional list of children

    children takes the current model and returns children from sub-nodes.  these are combined with the children
    return by format.
    '''
    line, extra = format(model)
    yield line
    all_children = (list(extra) if extra else []) + list(children(model))
    for child in all_children:
        last = child == all_children[-1]
        prefix = '`-' if last else '+-'
        for line in to_tree(child, format, children):
            yield prefix + line
            prefix = '  ' if last else '| '


def to_csv(model, format, children):
    '''
    same interface as above, but returns csv (kinda).
    '''
    parent_line, extra = format(model)
    all_children = (list(extra) if extra else []) + list(children(model))
    displayed = False
    for child in all_children:
        for child_line in to_csv(child, format, children):
            yield parent_line + ',' + child_line
            displayed = True
    if not displayed:
        yield parent_line
