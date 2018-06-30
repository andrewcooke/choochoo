
from .focus import OnFocus


class Factory:

    def __init__(self, tabs=None, bar=None, binder=None):
        self.tabs = tabs
        self.binder = binder
        self.bar = bar

    def __call__(self, widget, message=None, bindto=None, key=False, **binder_kargs):
        if self.binder:
            if bindto:
                if key:
                    widget = self.binder.bind_key(widget, bindto, **binder_kargs)
                else:
                    widget = self.binder.bind(widget, bindto, **binder_kargs)
        elif bindto:
            raise Exception('Binding but no binder for %s (type %s)' % (widget, type(widget)))
        if self.bar:
            if message:
                widget = OnFocus(widget, message, self.bar)
        elif message:
            raise Exception('Message but no bar for %s (type %s)' % (widget, type(widget)))
        if self.tabs is not None:
            widget = self.tabs.append(widget)
        return widget

