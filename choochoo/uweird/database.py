
import datetime as dt
from collections.abc import MutableMapping

from urwid import connect_signal


# transforms
DATE_ORDINAL = (lambda x: x if x is None else dt.date.fromordinal(x),
                lambda x: x if x is None else x.toordinal())


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
    """
    Idea stolen from https://martinfowler.com/eaaDev/uiArchs.html
    but I may have misunderstood.
    """

    def __init__(self, db, log, transforms=None, defaults=None):
        self._db = db
        self._log = log
        self._data = {}
        self._widget_names = {}
        self._defaults = defaults if defaults else {}
        self._set_defaults()
        self._dbdata = TransformedView(self._data, transforms)

    def bind(self, widget, name):
        """
        Call with each widget in turn.  The name should be the column name in
        the database.
        """
        self._log.debug('Binding %s as %s' % (widget, name))
        connect_signal(widget, 'change', self._save_widget_value)
        self._widget_names[widget] = name

    def _set_defaults(self):
        for name in self._widget_names.values():
            if name in self._defaults:
                self._data[name] = self._defaults[name]
            else:
                self._data[name] = None

    def _save_widget_value(self, widget, value):
        self._log.debug('Saving %s=%s' % (self._widget_names[widget], value))
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
        Subclasses must write data to database.
        """
        raise NotImplemented()

    def read_values_from_db(self):
        """
        Subclasses must read data from the database.
        """
        raise NotImplemented()


class DynamicBinder(Binder):

    def __init__(self, db, log, transforms=None, defaults=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._key_name = None

    def bind_key(self, widget, name):
        self._key_name = name
        self.bind(widget, name)

    def _save_widget_value(self, widget, value):
        # only trigger database access if the key is changing
        if widget and self._widget_names[widget] == self._key_name and \
                (self._key_name not in self._data or value != self._data[self._key_name]):
            if self._key_name in self._dbdata:
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


class SingleTableDynamic(DynamicBinder):
    """
    Read/write all values from a single table in the database.
    """

    def __init__(self, db, log, table, transforms=None, defaults=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._table = table

    def write_values_to_db(self):
        cmd = 'replace into %s (' % self._table
        cmd += ', '.join(self._dbdata.keys())
        cmd += ') values ('
        cmd += ', '.join(['?'] * (len(self._dbdata)))
        cmd += ')'
        values = list(self._dbdata.values())
        self._log.debug('%s / %s' % (cmd, values))
        self._db.db.execute(cmd, values)

    def read_values_from_db(self):
        cmd = 'select '
        cmd += ', '.join(self._widget_names.values())
        cmd += ' from %s where %s = ?' % (self._table, self._key_name)
        values = [self._dbdata[self._key_name]]
        self._log.debug('%s / %s' % (cmd, values))
        row = self._db.db.execute(cmd, values).fetchone()
        if row is None:
            self._set_defaults()
        else:
            for name in self._widget_names.values():
                self._log.debug('Read %s=%s' % (name, row[name]))
                self._dbdata[name] = row[name]
        # in case not include in read, or defaults used
        self._dbdata[self._key_name] = values[0]


class StaticBinder(Binder):

    def __init__(self, db, log, transforms=None, defaults=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)

    def save(self, unsued_widget):
        self.write_values_to_db()

    def reset(self, unused_Widget):
        self.read_values_from_db()

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


class SingleTableStatic(StaticBinder):

    def __init__(self, db, log, table, key_name='id', transforms=None, defaults=None, insert_callback=None):
        super().__init__(db, log, transforms=transforms, defaults=defaults)
        self._table = table
        self._key_name = key_name
        self._insert_callback = insert_callback

    def read_row(self, row):
        if row is None:
            self._set_defaults()
        else:
            for name in row.keys():
                self._log.debug('Read %s=%s' % (name, row[name]))
                self._dbdata[name] = row[name]
        self._broadcast_values_to_widgets()

    def write_values_to_db(self):
        replace = self._key_name in self._dbdata
        cmd = '%s into %s (' % ('replace' if replace else 'insert', self._table)
        cmd += ', '.join(self._dbdata.keys())
        cmd += ') values ('
        cmd += ', '.join(['?'] * (len(self._dbdata)))
        cmd += ')'
        values = list(self._dbdata.values())
        self._log.debug('%s / %s' % (cmd, values))
        self._db.db.execute(cmd, values)
        if not replace:
            self._dbdata[self._key_name] = self._db.db.execute('select last_insert_rowid()').fetchone()[0]
            if self._insert_callback: self._insert_callback()

    def read_values_from_db(self):
        if self._key_name in self._dbdata:
            cmd = 'select '
            names = [self._key_name]
            names.extend(self._widget_names.values())
            cmd += ', '.join(names)
            cmd += ' from %s where %s = ?' % (self._table, self._key_name)
            values = [self._dbdata[self._key_name]]
            self._log.debug('%s / %s' % (cmd, values))
            row = self._db.db.execute(cmd, values).fetchone()
        else:
            row = None
        self.read_row(row)
