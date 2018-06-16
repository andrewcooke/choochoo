
from collections.abc import MutableMapping

from urwid import connect_signal, Edit, WidgetWrap

from .focus import FocusAttr
from .widgets import SquareButton


class TransformedView(MutableMapping):

    def __init__(self, data, transforms=None):
        self.__data = data
        if transforms is None: transforms = {}
        self.__transforms = transforms

    def __getitem__(self, name):
        value = self.__data[name]
        if name in self.__transforms:
            value = self.__transforms[name][1](value)
        return value

    def __setitem__(self, name, value):
        if name in self.__transforms:
            value = self.__transforms[name][0](value)
        self.__data[name] = value

    def __delitem__(self, name):
        raise NotImplemented()

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return self.__data.__iter__()


class Binder:

    def __init__(self, db, log, transforms=None):
        self._db = db
        self._log = log
        self._data = {}
        self._widget_names = {}
        self._dbdata = TransformedView(self._data, transforms)

    def bind(self, widget, name):
        """
        Call with each widget in turn.  The name should be the column name in
        the database.
        """
        connect_signal(widget, 'change', self._save_widget_value)
        self._widget_names[widget] = name

    def _save_widget_value(self, widget, value):
        self._data[self._widget_names[widget]] = value

    def _broadcast_values_to_widgets(self):
        for widget in self._widget_names:
            name = self._widget_names[widget]
            value = self._data[name]
            self._log.debug('Setting %s=%s on %s' % (name, value, widget))
            if hasattr(widget, 'state'):
                widget.state = value
            elif hasattr(widget, 'set_edit_text'):
                widget.set_edit_text(value)
            else:
                self._log.error('Cannot set value on %s (%s)' % (widget, dir(widget)))

    def write_values_to_db(self):
        """
        Subclasses must write data to database using the key.
        """
        raise NotImplemented()

    def read_values_from_db(self):
        """
        Subclasses must read data from the database using the key.
        """
        raise NotImplemented()


class KeyedBinder(Binder):
    """
    Associate a set of fields with the database via a single key.

    Idea stolen from https://martinfowler.com/eaaDev/uiArchs.html
    but I may have misunderstood.
    """

    def __init__(self, db, log, transforms=None):
        super().__init__(db, log, transforms)
        self._key = None

    def bind_key(self, widget, name):
        self._key = name
        self.bind(widget, name)

    def _save_widget_value(self, widget, value):
        # only trigger database access if the key is changing
        if widget and self._widget_names[widget] == self._key and \
                (self._key not in self._data or value != self._data[self._key]):
            if self._key in self._dbdata:
                self.write_values_to_db()
            super()._save_widget_value(widget, value)
            self.read_values_from_db()
            self._broadcast_values_to_widgets()
        else:
            super()._save_widget_value(widget, value)

    def write_values_to_db(self):
        """
        Subclasses must write data to database using the key.
        """
        raise NotImplemented()

    def read_values_from_db(self):
        """
        Subclasses must read data from the database using the key.
        """
        raise NotImplemented()


class SingleTableBinder(KeyedBinder):
    """
    Read/write all values from a single table in the database.
    """

    def __init__(self, db, log, table, transforms=None):
        super().__init__(db, log, transforms=transforms)
        self._table = table

    def write_values_to_db(self):
        cmd = 'replace into %s (%s, ' % (self._table, self._key)
        cmd += ', '.join(self._dbdata.keys())
        cmd += ') values ('
        cmd += ', '.join(['?'] * (len(self._dbdata) + 1))
        cmd += ')'
        values = [self._dbdata[self._key]]
        values.extend(self._dbdata.values())
        self._log.debug('%s / %s' % (cmd, values))
        self._db.db.execute(cmd, values)

    def read_values_from_db(self):
        cmd = 'select '
        cmd += ', '.join(self._widget_names.values())
        cmd += ' from %s where %s = ?' % (self._table, self._key)
        values = [self._dbdata[self._key]]
        self._log.debug('%s / %s' % (cmd, values))
        row = self._db.db.execute(cmd, values).fetchone()
        for name in self._widget_names.values():
            try:
                self._log.debug('Read %s=%s' % (name, row[name]))
                self._dbdata[name] = row[name]
            except TypeError as e:
                self._log.error(e)
                self._dbdata[name] = None


class NoneProofEdit(Edit):

    def __init__(self, caption='', edit_text='', **kargs):
        super().__init__(caption=caption, edit_text='' if edit_text is None else edit_text, **kargs)

    def set_edit_text(self, text):
        if text is None:
            text = ''
        super().set_edit_text(text)


class Nullable(WidgetWrap):
    """
    make_widget must be able to generate a default state when called with no args.
    """

    def __init__(self, replacement, make_widget, state=None):
        self.__replacement = FocusAttr(SquareButton(replacement))
        self.__make_widget = make_widget
        if state is None:
            super().__init__(self.__replacement)
        else:
            super().__init__(make_widget(state))

    def __set_state(self, state):
        if state is None:
            self._w = self.__replacement
        elif self._w == self.__replacement:
            self._w = self.__make_widget(state)
        else:
            self._w.state = state
        self._invalidate()

    def __get_state(self):
        if self._w == self.__replacement:
            return None
        else:
            return self._w.state

    state = property(__get_state, __set_state)

    def keypress(self, size, key):
        if self._w == self.__replacement:
            if self._command_map[key] == 'activate':
                self._w = self.__make_widget()
                self._invalidate()
                return
        else:
            if key in ('delete', 'backspace'):
                self._w = self.__replacement
                self._invalidate()
                return
        try:
            return self._w.keypress(size, key)
        except AttributeError:
                return key

