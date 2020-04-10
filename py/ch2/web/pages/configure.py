from json import loads
from logging import getLogger

from ...commands.configure import load, delete
from ...commands.help import HTML, filter, parse, P, LI, PRE
from ...commands.import_ import Record, import_path
from ...config.utils import profiles
from ...lib import time_to_local_time
from ...lib.utils import restart_self
from ...migrate.import_ import available_versions
from ...migrate.import_.activity import activity_imported
from ...migrate.import_.constant import constant_imported
from ...migrate.import_.diary import diary_imported
from ...migrate.import_.kit import kit_imported
from ...sql import SystemConstant, Constant, StatisticJournal

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
SINGLE = 'single'
TIME = 'time'
VALUE = 'value'
VALUES = 'values'
VERSION = 'version'
VERSIONS = 'versions'


class Configure:

    def __init__(self, sys, db, base):
        self.__sys = sys
        self.__db = db
        self.__base = base
        self.__html = HTML(delta=1, parser=filter(parse, yes=(P, LI, PRE)))

    def is_configured(self):
        return bool(self.__sys.get_constant(SystemConstant.DB_VERSION, none=True))

    def html(self, text):
        return self.__html.str(text)

    def read_profiles(self, request, s):
        fn_argspec_by_name = profiles()
        version = self.__sys.get_constant(SystemConstant.DB_VERSION, none=True)
        data = {PROFILES: {name: self.html(fn_argspec_by_name[name][0].__doc__) for name in fn_argspec_by_name},
                CONFIGURED: bool(version),
                DIRECTORY: self.__base}
        if data[CONFIGURED]: data[VERSION] = version
        return data

    def write_profile(self, request, s):
        data = request.json
        load(self.__sys, s, False, data[PROFILE])

    def delete(self, request, s):
        delete(self.__sys, self.__base, True)
        # now we need to restart because the database connections exist
        restart_self()

    def read_import(self, request, s):
        record = Record()
        return {IMPORTED: {DIARY: diary_imported(record, self.__db),
                           ACTIVITY: activity_imported(record, self.__db),
                           KIT: kit_imported(record, self.__db),
                           CONSTANT: constant_imported(record, self.__db)},
                VERSIONS: available_versions(self.__base)}

    def write_import(self, request, s):
        data = request.json
        log.debug(data)
        record = Record()
        import_path(record, self.__base, data[VERSION], self.__db)
        return record.json()

    def read_constants(self, request, s):
        html = HTML()
        return [self.read_constant(s, constant)
                for constant in s.query(Constant).order_by(Constant.name).all()]

    def read_constant(self, s, constant):
        as_json = bool(constant.validate_cls)
        values = [{TIME: time_to_local_time(statistic.time),
                   VALUE: loads(statistic.value) if as_json else statistic.value}
                  for statistic in s.query(StatisticJournal).
                      filter(StatisticJournal.source_id == constant.id).all()]
        return {NAME: constant.name,
                SINGLE: constant.single,
                DESCRIPTION: self.html(constant.statistic_name.description),
                VALUES: values}

    def write_constant(self, request, s):
        data = request.json
        log.debug(data)
