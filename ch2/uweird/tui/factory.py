
from .focus import OnFocus, FocusAttr


class Factory:

    def __init__(self, tabs=None, bar=None):
        self.tabs = tabs
        self.bar = bar

    def __call__(self, widget, message=None):
        if self.bar:
            if message:
                widget = OnFocus(widget, message, self.bar)
        elif message:
            raise Exception('Message but no bar for %s (type %s)' % (widget, type(widget)))
        if self.tabs is not None:
            widget = self.tabs.append(widget)
        else:
            widget = FocusAttr(widget)
        return widget
