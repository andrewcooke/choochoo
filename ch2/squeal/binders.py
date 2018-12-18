
from sqlalchemy import inspect
from urwid import connect_signal, disconnect_signal


class Binder:

    # this works in two ways:
    # 1 - a single row is updated.  key values must be supplied in defaults and composite
    #     keys are possible, but modifying the key values raises an exception
    # 2 - rows can be navigated.  a single primary key only.  when changed, the session
    #     is committed and a new value read from the database.

    def __init__(self, log, session, widget, table=None, multirow=False, defaults=None, instance=None):
        if defaults is None: defaults = {}
        self.__log = log
        self.__session = session
        self.__widget = widget
        self.__multirow = multirow
        self.__defaults = defaults
        self.__ignore_changes = False
        self.__table = table if table else type(instance)
        self.__primary_keys = tuple(map(lambda column: column.name, inspect(self.__table).primary_key))
        if self.__multirow and len(self.__primary_keys) > 1:
            raise Exception('Composite key not compatible with multirow')
        if instance:
            self.instance = instance
            self.__from_database = all(getattr(instance, key) is not None for key in self.__primary_keys)
        else:
            self.instance = None
            self.__from_database = False
            self.__read()
        self.__bind()

    def __bind(self,):
        self.__log.debug('Binding %s to %s' % (self.instance, self.__widget))
        save_ignore, self.__ignore_changes = self.__ignore_changes, True
        try:
            for column in inspect(self.__table).columns:
                name = column.name
                value = getattr(self.instance, name)
                if not name.startswith('_'):
                    try:
                        widget = getattr(self.__widget, name)
                        self.__log.debug('Setting %s=%s on %s' % (name, value, widget))
                        while widget:
                            if self._try_bind(column, value, widget):
                                break
                            widget = self._try_descend(column, value, widget)
                    except AttributeError as e:
                        self.__log.warning('Cannot find %s member of %s (%s): %s' %
                                        (name, self.__widget, dir(self.__widget), e))
        finally:
            self.__ignore_changes = save_ignore

    def _try_descend(self, column, value, widget):
        if hasattr(widget, 'base_widget') and widget != widget.base_widget:
            return widget.base_widget
        elif hasattr(widget, '_wrapped_widget') and widget != widget._wrapped_widget:
            return widget._wrapped_widget
        else:
            self.__log.error('Cannot set %s on %s (%s)' % (column.name, widget, dir(widget)))
            return None

    def _try_bind(self, column, value, widget):
        if hasattr(widget, 'state'):
            self.__bind_state(column, value, widget)
            return True
        elif hasattr(widget, 'set_edit_text'):
            self.__bind_edit(column, value, widget)
            return True
        return False

    def __with_default(self, column, value):
        if not column.nullable and value is None:
            if column.server_default:
                value = column.server_default.arg
                setattr(self.instance, column.name, value)
            else:
                raise Exception('Column %s is not nullable, but has no default' % column)
        return value

    def __bind_state(self, column, value, widget):
        widget.state = self.__with_default(column, value)
        self.__connect(widget, column.name)

    def __bind_edit(self, column, value, widget):
        widget.set_edit_text(self.__with_default(column, value))
        self.__connect(widget, column.name)

    def __connect(self, widget, name):
        # we don't use weak args because we want the binder to be around as long as the widget
        user_args = [name]
        self.__log.debug('Disconnecting %s' % widget)
        disconnect_signal(widget, 'change', self.__change_callback, user_args=user_args)
        self.__log.debug('Connecting %s' % widget)
        connect_signal(widget, 'change', self.__change_callback, user_args=user_args)

    def __change_callback(self, name, widget, value):
        self.__log.debug('Change %s=%s for %s (%s)' % (name, value, widget, self.instance))
        if name in self.__primary_keys:
            if self.__multirow:
                self.__session.commit()
                self.__defaults[name] = value
                self.__read()
                self.__bind()
            elif value != getattr(self.instance, name):
                raise Exception('Primary key (%s) modified, but not multirow')
        else:
            if not self.__from_database and not self.__ignore_changes:
                self.__log.debug('Adding %s to session' % self.instance)
                self.__session.add(self.instance)
            self.__log.debug('Setting %s=%s on %s' % (name, value, self.instance))
            setattr(self.instance, name, value)

    def __default_instance(self):
        return self.__table(**self.__defaults)

    def __read(self):
        self.instance = None
        if self.__defaults:
            self.__log.debug('Reading new %s' % self.__table)
            query = self.__session.query(self.__table)
            for (k, v) in self.__defaults.items():
                query = query.filter(getattr(self.__table, k) == v)
            self.instance = query.one_or_none()
        if self.instance:
            self.__from_database = True
        else:
            self.__from_database = False
            self.__log.debug("No database entry, so creating default from %s" % self.__defaults)
            self.instance = self.__default_instance()

    def reset(self):
        """
        Revert the widget to the values in the database (or defaults, if it is not from there).
        """
        if self.instance:
            self.__log.debug('Refreshing %s' % self.instance)
            if self.__from_database:
                self.__session.refresh(self.instance)
                self.__bind()
            else:
                self.__log.debug('Expunging %s' % self.instance)
                self.__session.expunge(self.instance)
                self.instance = self.__default_instance()
                self.__bind()

    def delete(self):
        """
        Remove from the database.
        """
        if self.instance:
            self.__log.debug('Deleting %s' % self.instance)
            self.__session.delete(self.instance)
            self.instance = None
