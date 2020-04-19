
from collections import defaultdict
from logging import getLogger
from os.path import splitext

from werkzeug import Response

from ch2.commands.args import base_system_path, THUMBNAIL
from ch2.commands.thumbnail import parse_activity, save_to_cache

log = getLogger(__name__)


class ContentType:

    CONTENT_TYPE = defaultdict(lambda: 'text/plain', {
        'js': 'text/javascript',
        'html': 'text/html',
        'css': 'text/css',
        'png': 'image/png'
    })

    def set_content_type(self, response, name):
        ext = splitext(name)[1].lower()
        if ext:
            ext = ext[1:]
        response.content_type = self.CONTENT_TYPE[ext]


class Base(ContentType):

    def __init__(self, base, subdir):
        self._base = base
        self._subdir = subdir

    def __call__(self, request, s, file):
        try:
            path = base_system_path(self._base, subdir=self._subdir, file=file)
            log.debug(f'Reading {path}')
            with open(path, 'rb') as input:
                response = Response(input.read())
            self.set_content_type(response, file)
            return response
        except Exception as e:
            log.warning(f'Error serving {file}: {e}')
            raise


class Thumbnail(Base):

    def __init__(self, base):
        super().__init__(base, THUMBNAIL)

    def __call__(self, request, s, activity):
        activity_id = parse_activity(s, activity)
        save_to_cache(self._base, s, activity_id)
        return super().__call__(request, s, f'{activity_id}.png')
