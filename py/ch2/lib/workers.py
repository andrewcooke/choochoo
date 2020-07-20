from contextlib import contextmanager
from logging import getLogger
from os import getpid
from sys import argv

from math import floor

log = getLogger(__name__)


def command_root():
    try:
        with open(f'/proc/{getpid()}/cmdline', 'rb') as f:
            line = f.readline()

            def parse():
                word = bytearray()
                for char in line:
                    if char:
                        word.append(char)
                    else:
                        yield word.decode('utf8')
                        word = bytearray()

            words = list(parse())
            log.debug(f'Parsed /proc/{getpid()}/cmdline as {" ".join(words)}')
            if len(argv) > 1:
                i = words.index(argv[1])
                words = words[:i]
            ch2 = ' '.join(words)
            if 'unittest' in ch2:
                log.warning(f'Appear to be inside test runner: {ch2}')
                ch2 = 'python -m ch2'
            log.debug(f'Using command "{ch2}"')
            return ch2
    except:
        log.warning('Cannot read /proc so assuming that ch2 is started on the command line as "ch2"')
        return 'ch2'


class ProgressTree:

    def __init__(self, size_or_weights, parent=None):
        if isinstance(size_or_weights, int):
            self.__size = size_or_weights
            self.__weights = [1] * self.__size
        else:
            self.__weights = size_or_weights
            self.__size = sum(self.__weights)
        self.__progress = 0
        self.__children = []
        self.__parent = parent
        if parent:
            parent.register(self)

    def _build_weights(self, weights):
        if isinstance(weights, int):
            return [1/weights] * weights

    def register(self, child):
        self.__children.append(child)
        if len(self.__children) > self.__size:
            raise Exception(f'Progress children exceeded size {len(self.__children)}/{self.__size}')

    def local_progress(self):
        if self.__children:
            progress = sum(child.local_progress() * weight
                           for (child, weight) in zip(self.__children, self.__weights)) / self.__size
            return progress
        else:
            return self.__progress / self.__size if self.__size else 1

    def progress(self):
        if self.__parent:
            return self.__parent.progress()
        else:
            return self.local_progress()

    def _log_progress(self):
        local = floor(100 * self.local_progress())
        progress = floor(100 * self.progress())
        log.info(f'Progress: {progress:3d}% (locally {local}%)')

    def increment(self, n=1):
        if self.__children:
            raise Exception('Incrementing a parent node')
        self.__progress += n
        if self.__progress > self.__size:
            raise Exception(f'Progress counter exceeded size {self.__progress}/{self.__size}')
        self._log_progress()

    def complete(self):
        self.__progress = self.__size
        self._log_progress()

    @contextmanager
    def increment_or_complete(self, n=1):
        try:
            yield None
            self.increment(n=n)
        except Exception as e:
            log.debug(f'Completing on {type(e)}: {e}')
            self.complete()
            raise


class SystemProgressTree(ProgressTree):

    def __init__(self, data, name, size_or_weights):
        super().__init__(size_or_weights)
        self.__data = data
        self.name = name
        data.create_progress(name)

    def progress(self):
        progress = super().progress()
        self.__data.update_progress(self.name, percent=floor(100 * progress))
        return progress

    def complete(self):
        super().complete()
        self.__data.remove_progress(self.name)
