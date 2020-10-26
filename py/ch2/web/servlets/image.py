from logging import getLogger

from werkzeug import Response
from werkzeug.wrappers import ETagResponseMixin

from . import ContentType
from ...commands.args import IMAGE_DIR

log = getLogger(__name__)


class CacheResponse(Response, ETagResponseMixin):
    pass


class BaseImage(ContentType):

    def __init__(self, config):
        self._image_dir = config.args._format_path(IMAGE_DIR)

    def _serve(self, path):
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


class Thumbnail(BaseImage):

    def __call__(self, request, s, activity, sector=None):
        from ...commands.thumbnail import create_in_cache
        path = create_in_cache(self._image_dir, s, activity, sector_id=sector)
        return self._serve(path)


class Sparkline(BaseImage):

    def __call__(self, request, s, statistic, sector, activity):
        from ...commands.sparkline import create_in_cache
        path = create_in_cache(self._image_dir, s, statistic, sector_id=sector, activity_id=activity)
        return self._serve(path)
