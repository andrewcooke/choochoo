
from importlib.resources import read_binary
from logging import getLogger
from os.path import split, sep

from werkzeug import Response

from ..servlets.base import ContentType

log = getLogger(__name__)


class Static(ContentType):

    def __init__(self, package):
        if package.startswith('.'):
            self.__package = __name__.rsplit('.', maxsplit=1)[0] + package
        else:
            self.__package = package

    def __call__(self, request, s, path):
        package, file = self.parse_path(path)
        for (extension, encoding) in (('.gz', 'gzip'), ('', None)):
            if not encoding or encoding in request.accept_encodings:
                file_extn = file + extension
                try:
                    log.debug(f'Reading {file_extn} from {package}')
                    response = Response(read_binary(package, file_extn))
                    if encoding:
                        response.content_encoding = encoding
                    self.set_content_type(response, file)
                    return response
                except Exception as e:
                    if encoding:
                        log.debug(f'Encoding {encoding} not supported by server: {e}')
                    else:
                        log.warning(f'Error serving {file}: {e}')
            else:
                log.debug(f'Encoding {encoding} not supported by client')
        raise Exception(f'File not found: {file}')

    def parse_path(self, path):
        package = self.__package
        head, tail = split(path)
        if not tail:
            raise Exception(f'{path} is a directory')
        if tail == '__init__.py':
            raise Exception('Refusing to serve package marker')
        if '.' in head:
            raise Exception(f'Package separators in {head}')
        if head:
            package += '.' + '.'.join(head.split(sep))
        return package, tail
