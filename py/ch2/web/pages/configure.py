
from logging import getLogger

from ..json import JsonResponse
from ...commands.configure import load, delete
from ...commands.help import HTML, filter, parse, P, LI, PRE
from ...config.utils import profiles
from ...lib.utils import restart_self
from ...sql import Pipeline, SystemConstant

log = getLogger(__name__)

PROFILE = 'profile'
PROFILES = 'profiles'
CONFIGURED = 'configured'
DIRECTORY = 'directory'
VERSION = 'version'


class Configure:

    def __init__(self, sys, base):
        self.__sys = sys
        self.__base = base

    def is_configured(self):
        return bool(self.__sys.get_constant(SystemConstant.DB_VERSION, none=True))

    def read_profiles(self, request, s):

        from ..server import DATA

        def fmt(text):
            return HTML(delta=1, parser=filter(parse, yes=(P, LI, PRE))).str(text)

        fn_argspec_by_name = profiles()
        version = self.__sys.get_constant(SystemConstant.DB_VERSION, none=True)
        data = {PROFILES: {name: fmt(fn_argspec_by_name[name][0].__doc__) for name in fn_argspec_by_name},
                CONFIGURED: bool(version),
                DIRECTORY: self.__base}
        if data[CONFIGURED]: data[VERSION] = version
        return JsonResponse({DATA: data})

    def write_profile(self, request, s):
        data = request.json
        load(self.__sys, s, False, data[PROFILE])

    def delete(self, request, s):
        delete(self.__sys, self.__base, True)
        # now we need to restart because the dabatase connections exist
        restart_self()
