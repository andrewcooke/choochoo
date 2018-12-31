
from io import StringIO
from contextlib import AbstractContextManager
from logging import getLogger
from os import makedirs
from os.path import exists, dirname
from re import sub

HEX_ADDRESS = lambda s: sub(r'0x[0-9a-f]{8,}', 'ADDRESS', s)


class BufferContext(AbstractContextManager):

    def __init__(self, log, path, filters):
        self._log = log
        self._path = path
        self._filters = filters
        self._buffer = StringIO()

    def __enter__(self):
        return self._buffer

    def _filter(self, s):
        if self._filters:
            for filter in self._filters:
                s = filter(s)
        return s


class ComparisonContext(BufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self._path, 'r') as input:
            target = input.read()
            self._test.assertEqual(target, self._filter(self._buffer.getvalue()))


class DumpContext(BufferContext):

    def __exit__(self, exc_type, exc_val, exc_tb):
        makedirs(dirname(self._path), exist_ok=True)
        with open(self._path, 'w') as output:
            output.write(self._filter(self._buffer.getvalue()))
        self._log.info('Wrote data to "%s"' % self._path)


class OutputMixin:

    def _resolve_log(self, log):
        '''
        Allow mixin with classes that may have their own log.
        '''
        if hasattr(self, 'log'):
            log = log or self.log
        if hasattr(self, '_log'):
            log = log or self._log
        return log or getLogger()

    def assertFileMatch(self, path, log=None, filters=None):
        log = self._resolve_log(log)
        if exists(path):
            return ComparisonContext(log, path, filters, self)
        else:
            log.warning('File "%s" does not exist; will generate rather than check' % path)
            return DumpContext(log, path, filters)
