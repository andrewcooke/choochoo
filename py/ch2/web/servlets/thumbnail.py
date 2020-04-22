from logging import getLogger

from werkzeug import Response
from werkzeug.wrappers import ETagResponseMixin

from . import ContentType
from ...commands.args import base_system_path, THUMBNAIL
from ...commands.thumbnail import parse_activity, save_to_cache

log = getLogger(__name__)


class CacheResponse(Response, ETagResponseMixin):
    pass


class Thumbnail(ContentType):

    def __init__(self, base):
        self._base = base

    def __call__(self, request, s, activity):
        activity_id = parse_activity(s, activity)
        file = save_to_cache(self._base, s, activity_id)
        try:
            path = base_system_path(self._base, subdir=THUMBNAIL, file=file)
            log.debug(f'Reading {path}')
            with open(path, 'rb') as input:
                response = CacheResponse(input.read())
            self.set_content_type(response, file)
            response.cache_control.max_age = 3600
            return response
        except Exception as e:
            log.warning(f'Error serving {file}: {e}')
            raise
