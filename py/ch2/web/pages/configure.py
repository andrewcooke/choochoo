
from logging import getLogger

from ..json import JsonResponse
from ...config.utils import profiles
from ...sql import Pipeline

log = getLogger(__name__)

PROFILES = 'profiles'
CONFIGURED = 'configured'


class Configure:

    @staticmethod
    def get_configured(s):
        return bool(s.query(Pipeline).count())

    @staticmethod
    def read_profiles(request, s):
        from ..server import DATA
        fn_argspec_by_name = profiles()
        data = {PROFILES: {name: fn_argspec_by_name[name][0].__doc__ for name in fn_argspec_by_name},
                CONFIGURED: Configure.get_configured(s)}
        return JsonResponse({DATA: data})
