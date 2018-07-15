
from urwid import AttrMap, Widget, WidgetWrap, Text


class FocusWrap(WidgetWrap):
    """
    If we are wrapping a container, allow introspection of contents.
    """

    # we have to be careful here not not actually copy data, because
    # contents may be rebuilt.  so things are more dynamic than you
    # may expect - everything is looked up when needed,

    def _focus_target(self):
        try:
            self._w.focus_position  # test for access
            return self._w
        except:
            try:
                self._w.base_widget.focus_position  # test for access
                return self._w.base_widget
            except:
                # this ends up being thrown by the attributes
                raise AttributeError('Widget %s (type %s) has no focus' % (self._w, type(self._w)))

    def _get_contents(self):
        return self._focus_target().contents

    contents = property(_get_contents)

    def _get_focus_position(self):
        return self._focus_target().focus_position

    def _set_focus_position(self, focus):
        self._focus_target().focus_position = focus

    focus_position = property(_get_focus_position, _set_focus_position)


class Focus:
    """
    Store and apply a focus path.
    """

    def __init__(self, focus, log):
        self._focus = focus
        self._log = log

    def to(self, widget, key=None):
        self._log.debug('Applying %s to %s (type %s)' % (self._focus, widget, type(widget)))
        for focus in self._focus:
            widget = self._container(widget)
            try:
                widget.focus_position = focus
            except Exception:
                # the container may have changed
                # a common case is contents as list, so let's try setting to end of list
                try:
                    widget.focus_position = len(widget.contents) - 1
                except Exception as e:
                    self._log.error(e)
                    return
            self._log.debug('Set %s (%s) on %s (type %s)' % (focus, widget.focus_position, widget, type(widget)))
            try:
                self._log.debug('Target %s (%s)' % (widget._focus_target, widget._focus_target.focus_position))
            except AttributeError:
                pass
            widget = self._unpack_widget(widget.contents[widget.focus_position])

    def _container(self, w):
        while True:
            try:
                w.focus_position
                return w
            except Exception as e:
                if w.base_widget != w:
                    w = w.base_widget
                else:
                    raise

    def _unpack_widget(self, widgets):
        if not isinstance(widgets, tuple):
            widgets = [widgets]
        for widget in widgets:
            if isinstance(widget, Widget):
                return widget
        raise Exception('No widget in %s' % str(widgets))


class FocusFor(Focus):
    """
    Record focus from a complex container and then re-apply (eg when the widget
    has been rebuilt).
    """

    def __init__(self, widget, log):
        focus = []
        try:
            while True:
                widget = self._container(widget)
                focus.append(widget.focus_position)
                widget = self._unpack_widget(widget.contents[widget.focus_position][0])
        except:  # as far down as we can go
            pass
        super().__init__(focus, log)


class AttrChange(Exception):
    """
    Exception allowing widgets to telegraph a change in attributes to
    a surrounding FocusAttr.
    """

    def __init__(self, error):
        self.error = error
        super().__init__()


class FocusAttr(AttrMap):

    def __init__(self, w, plain=None, focus=None):
        if plain is None: plain = 'plain'
        if focus is None: focus = plain + '-focus'
        self._plain = plain
        self._focus = focus
        super().__init__(w, plain, focus)
        try:
            self.contents = self.base_widget.contents
        except AttributeError:
            pass

    def keypress(self, size, key):
        try:
            return self._original_widget.keypress(size, key)
        except AttrChange as e:
            if e.error:
                self.set_attr_map({None: 'error'})
                self.set_focus_map({None: 'error-focus'})
            else:
                self.set_attr_map({None: self._plain})
                self.set_focus_map({None: self._focus})


class MessageBar(WidgetWrap):
    """
    Central display for messages (eg help with keypress).
    Supports safe delete via keys (you can only delete your own message).
    """

    def __init__(self, default='alt-q to quit; alt-s to save; alt-x to quit without saving', attribute='bar'):
        self.__default = default
        self.__latest = None
        self.__text = Text(default, wrap='clip')
        super().__init__(FocusAttr(self.__text, plain=attribute))

    def set_text(self, markup, key=None):
        self.__text.set_text(markup)
        self.__latest = key

    def clear(self, key):
        if self.__latest == key:
            self.__text.set_text(self.__default)


class OnFocus(FocusWrap):
    """
    Set a message on the message bar when focus is enabled.
    This triggers changes during rendering, which will only be
    reflected in the output of items rendered after this target,
    This is why the message bar must be on the bottom of the app.
    """

    def __init__(self, widget, message, bar=None):
        self.__message = message
        self.__bar = bar
        self.__focus = False
        super().__init__(widget)

    def __update_focus(self, focus):
        if self.__bar:
            if focus != self.__focus:
                self.__focus = focus
                self.update_bar()

    def update_bar(self):
        # called from Nullable, when underlying widget changes without
        # any change in focus.
        if self.__focus:
            self.__bar.set_text(self.__message, key=self)
        else:
            self.__bar.clear(self)

    def render(self, size, focus=False):
        self.__update_focus(focus)
        return self._w.render(size, focus=focus)

    def rows(self, size, focus=False):
        self.__update_focus(focus)
        return self._w.rows(size, focus=focus)

    def pack(self, size, focus=False):
        self.__update_focus(focus)
        return self._w.pack(size, focus=focus)
