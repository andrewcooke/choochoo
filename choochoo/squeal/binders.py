from sqlalchemy import inspect
from urwid import connect_signal, disconnect_signal


def weak(target, attr, *args):
    return getattr(target, attr)(*args)


class Binder:

    # this works in two ways:
    # 1 - a single row is updated.  key values must be supplied in defaults and composite
    #     keys are possible, but modifying the key values raises an exception
    # 2 - rows can be navigated.  a single primary key only.  when changed, the session
    #     is committed and a new value read from the database.

    def __init__(self, log, session, widget, table, multirow=False, defaults=None):
        if defaults is None: defaults = {}
        self.__log = log
        self.__session = session
        self.__widget = widget
        self.__table = table
        self.__multirow = multirow
        self.__defaults = defaults
        self.__primary_keys = tuple(map(lambda column: column.name, inspect(table).primary_key))
        if self.__multirow and len(self.__primary_keys) > 1:
            raise Exception('Composite key not compatible with multirow')
        self.instance = None
        self.__read()
        self.__bind()

    def __bind(self):
        for (k, v) in vars(self.instance).items():
            if not k.startswith('_'):
                try:
                    w = getattr(self.__widget, k)
                    self.__log.debug('Setting %s=%s on %s' % (k, v, w))
                    if hasattr(w, 'state'):
                        self.__bind_state(k, v, w)
                    elif hasattr(w, 'set_edit_text'):
                        self.__bind_edit(k, v, w)
                    else:
                        self.__log.error('Cannot set value on %s (%s)' % (w, dir(w)))
                except AttributeError:
                    self.__log.warn('Cannot find %s member of %s' % (k, self.__widget))

    def __bind_state(self, name, value, widget):
        widget.state = value
        self.__connect(widget, name)

    def __bind_edit(self, name, value, widget):
        widget.set_edit_text(value)
        self.__connect(widget, name)

    def __connect(self, widget, name):
        weak_args = [self]
        # strings cannot be weak
        user_args = ['_change_callback', name]
        disconnect_signal(widget, 'change', weak, weak_args=weak_args, user_args=user_args)
        connect_signal(widget, 'change', weak, weak_args=weak_args, user_args=user_args)

    def _change_callback(self, name, widget, value):
        if name in self.__primary_keys:
            if self.__multirow:
                self.__session.commit()
                self.__defaults[name] = value
                self.__read()
                self.__bind()
            elif value != getattr(self.instance, name):
                raise Exception('Primary key (%s) modified, but not multirow')
        else:
            self.__log.debug('Setting %s=%s on %s' % (name, value, self.instance))
            setattr(self.instance, name, value)

    def __read(self):
        query = self.__session.query(self.__table)
        for (k, v) in self.__defaults.items():
            query = query.filter(getattr(self.__table, k) == v)
        self.instance = query.one_or_none()
        if not self.instance:
            self.instance = self.__table(**self.__defaults)

