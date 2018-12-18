
import datetime as dt
from collections.abc import MutableMapping
from functools import reduce
from operator import and_

from urwid import connect_signal


def or_none(f): return lambda x: x if x is None else f(x)


# transforms
DATE_ORDINAL = (or_none(dt.date.fromordinal), or_none(lambda x: x.toordinal()))


class TransformedView(MutableMapping):
    """
    Provide a transformed view of the data, with types more
    that match the database (eg exchange NULL and empty string,
    or convert ordinals to dates).
    """

    def __init__(self, data, transforms=None):
        self.__data = data
        if transforms is None: transforms = {}
        self.__transforms = transforms

    def set_transforms(self, name, transforms):
        self.__transforms[name] = transforms

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


UNSET = object()


class Binder:
    """
    Idea stolen from https://martinfowler.com/eaaDev/uiArchs.html
    but I may have misunderstood.
    """

    def __init__(self, db, log, transforms=None, defaults=None):
        self._db = db
        self._log = log
        self.__data = {}
        self._widget_names = {}
        self.__defaults = defaults if defaults else {}
        self._clear_and_set_defaults()
        self._dbview = TransformedView(self.__data, transforms)

    def bind(self, widget, name, transforms=None, default=UNSET):
        """
        Call with each widget in turn.  The name should be the column name in
        the database.
        """
        if transforms is not None:
            self._dbview.set_transforms(name, transforms)
        if default is not UNSET:
            self.__defaults[name] = default
        self._log.debug('Binding %s as %s' % (widget, name))
        connect_signal(widget, 'change', self._save_widget_value)
        self._widget_names[widget] = name
        return widget

    def save(self, unused_widget):
        """
        Target for button click.
        """
        self._write_values_to_db()

    def reset(self, unused_Widget):
        """
        Target for button click.
        """
        self._read_values_from_db()

    @staticmethod
    def connect(widget, name, callback):
        """
        Shortcut for inline wiring of callbacks.
        """
        connect_signal(widget, name, callback)
        return widget

    def _changed(self, name, value):
        """
        Has the value for this name changed?
        """
        return name not in self.__data or value != self.__data[name]

    def _clear_and_set_defaults(self):
        """
        Called before read.
        """
        self.__data.clear()
        for name in self.__defaults:
            if name not in self.__data:
                self.__data[name] = self.__defaults[name]

    def _save_widget_value(self, widget, value):
        """
        Update the value in the store, but don't write to disk (although
        sub-classes may auto-save if the key changes).
        """
        self._log.debug('Saving %s=%s' % (self._widget_names[widget], value))
        self.__data[self._widget_names[widget]] = value

    def _broadcast_values_to_widgets(self):
        """
        Attempt to set values on registered widgets.  Called by subclasses
        after reading from disk.
        """
        for widget in self._widget_names:
            name = self._widget_names[widget]
            value = self.__data[name]
            self._log.debug('Setting %s=%s on %s' % (name, value, widget))
            if hasattr(widget, 'state'):
                widget.state = value
            elif hasattr(widget, 'set_edit_text'):
                widget.set_edit_text(value)
            else:
                self._log.error('Cannot set value on %s (%s)' % (widget, dir(widget)))

    def _write_values_to_db(self):
        """
        Subclasses must write data to database.
        """
        raise NotImplemented()

    def _read_values_from_db(self):
        """
        Subclasses must read data from the database.
        """
        raise NotImplemented()


class DynamicBinder(Binder):
    """
    A binder that updates when a key value changes.
    """

    def __init__(self, db, log, transforms=None, defaults=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._key_name = None
        self._key_widget = None

    def bind_key(self, widget, name):
        self._key_widget = widget
        self._key_name = name
        return self.bind(widget, name)

    def bootstrap(self, state):
        self._save_widget_value(self._key_widget, state)

    def _save_widget_value(self, widget, value):
        # only trigger database access if the key is changing
        if widget == self._key_widget and self._changed(self._key_name, value):
            if self._key_name in self._dbview:
                self._write_values_to_db()
            else:
                self._log.debug('Cannot save values as no previous value for key %s' % self._key_name)
            super()._save_widget_value(widget, value)
            self._read_values_from_db()
            self._broadcast_values_to_widgets()
        else:
            super()._save_widget_value(widget, value)


class SingleTableDynamic(DynamicBinder):
    """
    Read/write all values from a single table in the database.
    """

    def __init__(self, db, log, table, transforms=None, defaults=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._table = table

    def _write_values_to_db(self):
        cmd = 'replace into %s (' % self._table
        cmd += ', '.join(self._dbview.keys())
        cmd += ') values ('
        cmd += ', '.join(['?'] * (len(self._dbview)))
        cmd += ')'
        values = list(self._dbview.values())
        self._log.debug('%s / %s' % (cmd, values))
        self._db.execute(cmd, values)

    def _read_values_from_db(self):
        cmd = 'select '
        cmd += ', '.join(self._widget_names.values())
        cmd += ' from %s where %s = ?' % (self._table, self._key_name)
        values = [self._dbview[self._key_name]]
        self._log.debug('%s / %s' % (cmd, values))
        row = self._db.execute(cmd, values).fetchone()
        self._clear_and_set_defaults()
        if row:
            for name in self._widget_names.values():
                self._log.debug('Read %s=%s' % (name, row[name]))
                self._dbview[name] = row[name]
        # in case not include in read, or defaults used
        self._dbview[self._key_name] = values[0]


class SingleTableStatic(Binder):
    """
    A binder associated with a single table whose key does not change.
    Typically the key value(s) are provided via defaults because they're
    not mutable via widgets.
    """

    def __init__(self, db, log, table, key_names='id', transforms=None, defaults=None,
                 insert_callback=None, autosave=False):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._table = table
        self._key_names = (key_names,) if isinstance(key_names, str) else key_names
        self._insert_callback = insert_callback
        self._autosave = autosave

    def _have_all_keys(self):
        return reduce(and_, (name in self._dbview for name in self._key_names))

    def _save_widget_value(self, widget, value):
        super()._save_widget_value(widget, value)
        if self._autosave:
            if self._have_all_keys():
                self._write_values_to_db()
            else:
                self._log.warning('Not saving because missing key values (%s)' % list(self._dbview.keys()))

    def read_row(self, row):
        self._clear_and_set_defaults()
        if row:
            for name in row.keys():
                self._log.debug('Read %s=%s' % (name, row[name]))
                self._dbview[name] = row[name]
        self._broadcast_values_to_widgets()

    def _write_values_to_db(self):
        if self._dbview:
            replace = self._have_all_keys()
            cmd = '%s into %s (' % ('replace' if replace else 'insert', self._table)
            cmd += ', '.join(self._dbview.keys())
            cmd += ') values ('
            cmd += ', '.join(['?'] * (len(self._dbview)))
            cmd += ')'
            values = list(self._dbview.values())
            self._log.debug('%s / %s' % (cmd, values))
            self._db.execute(cmd, values)
            if not replace and len(self._key_names) == 1:
                self._dbview[self._key_names[0]] = self._db.execute('select last_insert_rowid()', ()).fetchone()[0]
                if self._insert_callback: self._insert_callback()

    def _read_values_from_db(self):
        if self._have_all_keys():
            cmd = 'select '
            names = list(self._key_names)
            names.extend(self._widget_names.values())
            cmd += ', '.join(names)
            cmd += ' from %s where ' % self._table
            for i, name in enumerate(self._key_names):
                cmd += 'and ' if i else ''
                cmd += '%s = ? ' % name
            values = [self._dbview[name] for name in self._key_names]
            self._log.debug('%s / %s' % (cmd, values))
            row = self._db.execute(cmd, values).fetchone()
        else:
            row = None
        self.read_row(row)
