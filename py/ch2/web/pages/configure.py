
from logging import getLogger

from ..json import JsonResponse
from ...commands.help import HTML, filter, parse, P, LI, PRE
from ...config.utils import profiles
from ...sql import Pipeline, SystemConstant

log = getLogger(__name__)

PROFILES = 'profiles'
CONFIGURED = 'configured'
DIRECTORY = 'directory'


class Configure:

    def __init__(self, sys, base):
        self.__sys = sys
        self.__base = base

    def get_configured(self):
        return bool(self.__sys.get_constant(SystemConstant.DB_VERSION, none=True))

    def read_profiles(self, request, s):

        from ..server import DATA

        def fmt(text):
            return HTML(delta=1, parser=filter(parse, yes=(P, LI, PRE))).str(text)

        fn_argspec_by_name = profiles()
        data = {PROFILES: {name: fmt(fn_argspec_by_name[name][0].__doc__) for name in fn_argspec_by_name},
                CONFIGURED: self.get_configured(),
                DIRECTORY: self.__base}
        return JsonResponse({DATA: data})
