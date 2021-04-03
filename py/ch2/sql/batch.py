from collections import defaultdict
from itertools import groupby
from logging import getLogger
from weakref import WeakSet

from sqlalchemy import Sequence, select, text, inspect
from sqlalchemy.event import listen

log = getLogger(__name__)


class BatchLoader:

    def __init__(self, enabled=True, max_msg_cnt=10):
        self.enabled = enabled
        self.__max_msg_cnt = max_msg_cnt
        self.__sessions = WeakSet()
        self.reset()

    def reset(self):
        self.msgs = defaultdict(lambda: 0)
        self.sessions = 0
        self.calls = 0
        self.rows = 0

    def debug(self, msg):
        self.__message('debug', msg, log.debug)

    def warning(self, msg):
        self.__message('warning', msg, log.warning)

    def error(self, msg):
        self.__message('error', msg, log.error)

    def __message(self, type_, msg, log):
        self.msgs[(type_, msg)] += 1
        if self.msgs[(type_, msg)] <= self.__max_msg_cnt:
            log(msg)

    @staticmethod
    def __group_by_mapper(instances):
        sort_key = lambda model: type(model).__mapper__.base_mapper
        return groupby(sorted(instances, key=lambda x: str(sort_key(x))), key=sort_key)

    def __key_ok(self, mapper):
        if len(mapper.primary_key) == 1:
            key = mapper.primary_key[0]
            try:
                if key.type.python_type == int and \
                        key.autoincrement in ('auto', True) and \
                        key.table == mapper.local_table:
                    return True
                else:
                    self.warning(f'Unexpected key type for {mapper}')
            except Exception as e:
                # only debug here because we know this occurs with user-defined types
                # (like system constant)
                self.debug(f'Batch error with key {key}: {e!r}')
        else:
            self.warning(f'Composite primary key for {mapper}')
        return False

    @staticmethod
    def __ids(session, mapper, column, n):
        id_seq_name = f'{mapper.entity.__tablename__}_{column}_seq'
        schema = mapper.entity.__table__.metadata.schema
        sequence = Sequence(id_seq_name, schema=schema)
        return [int(row[0]) for row in session.connection().execute(
            select([sequence.next_value()]).select_from(text("generate_series(1, :num_values)")),
            num_values=n)]

    def __set_ids(self, session, mapper, column, missing):
        n = len(missing)
        for id, instance in zip(self.__ids(session, mapper, column, n), missing):
            setattr(instance, column, id)
        self.rows += 1

    def __populate(self, session):
        for mapper, instances in self.__group_by_mapper(session.new):
            if self.__key_ok(mapper):
                column = mapper.primary_key[0].name
                missing = [instance for instance in instances if getattr(instance, column) is None]
                if missing:
                    self.__set_ids(session, mapper, column, missing)
                else:
                    self.warning(f'ID already populated for {type(instances[0])}')

    @staticmethod
    def __group(session):
        instances = session.new
        sort_key = lambda instance: (str(type(instance)), inspect(instance).insert_order)
        for i, instance in enumerate(sorted(instances, key=sort_key)):
            inspect(instance).insert_order = i

    def enable(self, session):
        if self.enabled:
            if session not in self.__sessions:
                self.__sessions.add(session)
                self.sessions += 1
                listen(session, 'before_flush', self.__before_flush)
            else:
                log.warning(f'Tried to register session more than once')

    def __before_flush(self, session, context, instances):
        try:
            self.calls += 1
            if instances:
                self.warning('No batch support for explicit instances')
            else:
                self.__populate(session)
                self.__group(session)
        except Exception as e:
            self.error(e)
            raise
