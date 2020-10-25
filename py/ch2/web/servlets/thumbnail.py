from logging import getLogger

from werkzeug import Response
from werkzeug.wrappers import ETagResponseMixin

from . import ContentType
from ...commands.args import IMAGE_DIR
from ...commands.thumbnail import create_in_cache

log = getLogger(__name__)


class CacheResponse(Response, ETagResponseMixin):
    pass


class Thumbnail(ContentType):

    def __init__(self, config):
        self.__config = config

    def __call__(self, request, s, activity):
        activity_id = int(activity)
        dir = self.__config.args._format_path(IMAGE_DIR)
        path = create_in_cache(dir, s, activity_id)
        try:
            log.debug(f'Reading {path}')
            with open(path, 'rb') as input:
                response = CacheResponse(input.read())
            self.set_content_type(response, path)
            response.cache_control.max_age = 3600
            return response
        except Exception as e:
            log.warning(f'Error serving {path}: {e}')
            raise
