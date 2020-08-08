from json import loads, dumps
from logging import getLogger

from sqlalchemy import exists

from ..worker import run_and_wait
from ...commands.args import DB_VERSION, REMOVE, SCHEMA
from ...commands.db import add_profile, remove_schema
from ...commands.import_ import import_source
from ...common.md import HTML, parse, P, LI, PRE, filter_
from ...common.names import BASE, DB, WEB
from ...config.profile import get_profiles
from ...import_ import available_versions
from ...import_.activity import activity_imported
from ...import_.constant import constant_imported
from ...import_.diary import diary_imported
from ...import_.kit import kit_imported
from ...import_.segment import segment_imported
from ...lib import time_to_local_time, local_time_to_time
from ...lib.log import Record
from ...sql import Constant, StatisticJournal, ActivityJournal

log = getLogger(__name__)


ACTIVITY = 'activity'
CONFIGURED = 'configured'
CONSTANT = 'constant'
DESCRIPTION = 'description'
DIARY = 'diary'
DIRECTORY = 'directory'
IMPORTED = 'imported'
KIT = 'kit'
NAME = 'name'
PROFILE = 'profile'
PROFILES = 'profiles'
SEGMENT = 'segment'
SINGLE = 'single'
STATISTIC = 'statistic'
TIME = 'time'
VALUE = 'value'
VALUES = 'values'
VERSION = 'version'
VERSIONS = 'versions'


class Configure:

    def __init__(self, config):
        self.__config = config
        self.__html = HTML(delta=1, parser=filter_(parse, yes=(P, LI, PRE)))

    def is_configured(self):
        return not bool(self.__config.db.no_data())

    def is_empty(self, s):
        return not s.query(exists().where(ActivityJournal.id > 0)).scalar()

    def html(self, text):
        return self.__html.str(text)

    def read_profiles(self, request, s):
        fn_argspec_by_name = get_profiles()
        data = {PROFILES: {name: self.html(fn_argspec_by_name[name][0].__doc__) for name in fn_argspec_by_name},
                CONFIGURED: not bool(self.__config.db.no_data()),
                VERSION: DB_VERSION,
                DIRECTORY: self.__config.args[BASE]}
        return data

    def write_profile(self, request, s):
        data = request.json
        add_profile(self.__config._with(profile=data[PROFILE]))
        self.__config.reset()

    def delete(self, request, s):
        # run this as a sub-command so that the user sees that process are running if they try to multi-task
        run_and_wait(self.__config, f'{DB} {REMOVE} {SCHEMA}', Configure, f'{WEB}-{DB}.log')
        self.__config.reset()

    def read_import(self, request, s):
        record = Record(log)
        return {IMPORTED: {DIARY: diary_imported(record, self.__config.db),
                           ACTIVITY: activity_imported(record, self.__config.db),
                           KIT: kit_imported(record, self.__config.db),
                           CONSTANT: constant_imported(record, self.__config.db),
                           SEGMENT: segment_imported(record, self.__config.db)},
                VERSIONS: available_versions(self.__config)}

    def write_import(self, request, s):
        data = request.json
        record = Record(log)
        import_source(self.__config, record, data[VERSION])
        return record.json()

    def read_constants(self, request, s):
        return [self.read_constant(s, constant)
                for constant in s.query(Constant).order_by(Constant.name).all()]

    def read_constant(self, s, constant):
        as_json = bool(constant.validate_cls)
        values = [{TIME: time_to_local_time(statistic.time),
                   VALUE: loads(statistic.value) if as_json else statistic.value,
                   STATISTIC: statistic.id}
                  for statistic in s.query(StatisticJournal).
                      filter(StatisticJournal.source_id == constant.id).all()]
        return {NAME: constant.name,
                SINGLE: constant.single,
                DESCRIPTION: self.html(constant.statistic_name.description),
                VALUES: values}

    def write_constant(self, request, s):
        data = request.json
        log.debug(data)
        constant = Constant.from_name(s, data[NAME])
        value = data[VALUES][0][VALUE]
        if constant.validate_cls:
            value = dumps(value)
        time = data[VALUES][0][TIME]
        statistic_journal_id = data[VALUES][0][STATISTIC]
        if statistic_journal_id:
            journal = s.query(StatisticJournal). \
                filter(StatisticJournal.id == statistic_journal_id,
                       StatisticJournal.source_id == constant.id).one()
            journal.set(value)
            if not constant.single:
                journal.time = local_time_to_time(time)
        else:
            if constant.single and time:
                log.warning(f'Ignoring time for {constant.name}')
                time = 0.0
            constant.add_value(s, value, time=time)

    def delete_constant(self, request, s):
        data = request.json
        log.debug(data)
        s.delete(Constant.from_name(s, data))
