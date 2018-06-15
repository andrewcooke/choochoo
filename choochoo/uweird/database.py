
from urwid import connect_signal


class KeyedBinder:
    """
    Associate a set of fields with the database via a single key.

    Idea stolen from https://martinfowler.com/eaaDev/uiArchs.html
    but I may have misunderstood.
    """

    def __init__(self, db, log, key_transform=None):
        self._db = db
        self._log = log
        self._key = None
        self._data = {}
        self._widget_names = {}
        self._key_transform = key_transform

    def bind(self, widget, name):
        """
        Call with each widget in turn.  The name should be the column name in
        the database.
        """
        connect_signal(widget, 'change', self._save_widget_value, user_args=[name])
        self._widget_names[widget] = name

    def _save_widget_value(self, name, unused_widget, value):
        self._data[name] = value

    def update_key(self, key):
        """
        Connect to change signal for key.  Can also be called initially to load
        first data.
        """
        if self._key is not None:
            self.write_values_to_db()
        if self._key_transform:
            key = self._key_transform(key)
        self._key = key
        self.read_values_from_db()
        self._broadcast_values_to_widgets()

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


class SingleTableBinder(KeyedBinder):
    """
    Read/write all values from a single table in the database.
    """

    def __init__(self, db, log, table, key_name, key_transform=None):
        super().__init__(db, log, key_transform=key_transform)
        self._table = table
        self._key_name = key_name

    def write_values_to_db(self):
        cmd = 'replace into %s (%s, ' % (self._table, self._key_name)
        cmd += ', '.join(self._data.keys())
        cmd += ') values ('
        cmd += ', '.join(['?'] * (len(self._data) + 1))
        cmd += ')'
        values = [self._key]
        values.extend(self._data.values())
        self._log.debug('%s / %s' % (cmd, values))
        self._db.db.execute(cmd, values)

    def read_values_from_db(self):
        cmd = 'select '
        cmd += ', '.join(self._widget_names.values())
        cmd += ' from %s where %s = ?' % (self._table, self._key_name)
        self._log.debug('%s / %s' % (cmd, self._key))
        row = self._db.db.execute(cmd, (self._key, )).fetchone()
        self._data = {}
        for name in self._widget_names.values():
            try:
                self._data[name] = row[name]
                self._log.debug('Read %s=%s' % (name, self._data[name]))
            except TypeError as e:
                self._log.error(e)
                self._data[name] = None
