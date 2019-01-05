
from csv import reader
from io import StringIO
from contextlib import AbstractContextManager
from itertools import zip_longest
from logging import getLogger
from os import makedirs
from os.path import exists, dirname, split, join, splitext
from re import sub
from tempfile import NamedTemporaryFile

HEX_ADDRESS = lambda s: sub(r'0x[0-9a-f]{8,}', 'ADDRESS', s)


def DROP_HDR_CHK(us):
    for row in us:
        if row[0] in ('FileHeader', 'Checksum'):
            pass
        elif row[0] == 'DeveloperField':
            yield ['Data'] + row[1:]
        else:
            yield row


def EXCLUDE(name):
    def filter(data):
        for row in data:
            try:
                i = row.index(name)
                if not i % 3:
                    row = row[:i] + row[i+3:]
            except ValueError:
                pass
            yield row
    return filter


def sub_extn(path, extn):
    dir, file = split(path)
    return join(dir, '%s.%s' % (file.split('.')[0], extn))



class BufferContext(AbstractContextManager):

    def __init__(self, log, path, filters):
        self._log = log
        self._path = path
        self._filters = filters
        self._buffer = StringIO()

    def __enter__(self):
        return self._buffer

    def _filter(self, data):
        if self._filters:
            for filter in self._filters:
                data = filter(data)
        return data


class TextContext(BufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self._path, 'r') as input:
            target = input.read()
            result = self._filter(self._buffer.getvalue())
            if result != target:
                with NamedTemporaryFile(delete=False) as f:
                    f.write(result.encode())
                    self._log.info('Wrote copy of result to %s' % f.name)
                    self._log.info('Comparing with %s' % self._path)
                    self._log.info('diff %s %s' % (f.name, self._path))
            self._test.assertEqual(target, self._filter(self._buffer.getvalue()))


class DumpContext(BufferContext):

    def __exit__(self, exc_type, exc_val, exc_tb):
        makedirs(dirname(self._path), exist_ok=True)
        with open(self._path, 'w') as output:
            output.write(self._filter(self._buffer.getvalue()))
        self._log.info('Wrote data to "%s"' % self._path)


class CSVContext(BufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self._path, 'r') as them_in:
            them_reader = self._filter(reader(them_in))
            next(them_reader)  # drop titles
            us_reader = self._filter(reader(self._buffer.getvalue().splitlines()))
            for us_row, them_row in zip_longest(us_reader, them_reader):
                self.compare_rows(us_row, them_row)

    def compare_rows(self, us_row, them_row):
        self._test.assertEqual(us_row[0:3], them_row[0:3])
        excess = len(them_row) % 3
        if excess and not any(them_row[-excess:]):
            self._log.debug('Discarding %d empty values from reference' % excess)
            them_row = them_row[:-excess]
        while len(them_row) > len(us_row) + 2 and not any(them_row[-3:]):
            them_row = them_row[:-3]
        # after first 3 entries need to sort to be sure order is correct
        for us_nvu, them_nvu in zip_longest(sorted(grouper(cleaned(us_row[3:]), 3)),
                                            sorted(grouper(cleaned(them_row[3:]), 3))):
            if 'COMPOSITE' not in us_nvu[1]:
                self._test.assertEqual(us_nvu, them_nvu, self._path)


# https://docs.python.org/3/library/itertools.html#itertools-recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def cleaned(values):
    # want a good example for scaling errors, not zero
    # also, suspect some 0.0 might be 0.... (remove this later to check)
    return (value[:-2] if value.endswith('.0') else value for value in values)


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

    def assertTextMatch(self, path, log=None, filters=None):
        log = self._resolve_log(log)
        if exists(path):
            return TextContext(log, path, filters, self)
        else:
            log.warning('File "%s" does not exist; will generate rather than check' % path)
            return DumpContext(log, path, filters)


    def assertCSVMatch(self, path, log=None, filters=None):
        log = self._resolve_log(log)
        if exists(path):
            return CSVContext(log, path, filters, self)
        else:
            # the CSV file should have been generated using the SDK
            raise Exception('Could not open %s' % path)