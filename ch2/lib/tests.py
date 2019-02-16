from abc import abstractmethod
from csv import reader
from io import StringIO, BytesIO
from contextlib import AbstractContextManager
from itertools import zip_longest
from logging import getLogger
from os import makedirs
from os.path import exists, dirname, split, join
from re import sub
from tempfile import NamedTemporaryFile

from .utils import grouper

HEX_ADDRESS = lambda s: sub(r'0x[0-9a-f]{8,}', 'ADDRESS', s)


def EXC_HDR_CHK(data):
    for row in data:
        if row[0] in ('FileHeader', 'Checksum'):
            pass
        elif row[0] == 'DeveloperField':
            yield ['Data'] + row[1:]
        else:
            yield row


def EXC_FLD(name):
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


def EXC_MSG(name):
    def filter(data):
        for row in data:
            if row[0] == 'Data' and row[2] == name:
                yield row[:3]
            else:
                yield row
    return filter


def RNM_UNKNOWN(data):
    for row in data:
        for i in range(0, len(row), 3):
            if row[i].startswith('@'):
                row[i] = 'unknown'
        for i in range(2, len(row), 3):
            if row[i].startswith('MESSAGE'):
                row[i] = 'unknown'
        yield row


def ROUND_DISTANCE(data):
    for row in data:
        for i in range(0, len(row), 3):
            if row[i] == 'distance' and row[i+1] and '.' in row[i+1] and len(row[i+1].split('.')[1]) > 2:
                row[i+1] = '%.2f' % (float(row[i+1]) + 0.0000001)  # round up
        yield row


def sub_extn(path, extn):
    dir, file = split(path)
    return join(dir, '%s.%s' % (file.rsplit('.', 1)[0], extn))


def sub_dir(path, new_dir, offset):
    a, b = split(path)
    if offset:
        return join(sub_dir(a, new_dir, offset-1), b)
    else:
        return join(a, new_dir)


class BaseBufferContext(AbstractContextManager):

    def __init__(self, log, path, filters):
        self._log = log
        self._path = path
        self._filters = filters
        self._buffer = self._make_buffer()

    @abstractmethod
    def _make_buffer(self):
        raise NotImplementedError()

    def __enter__(self):
        return self._buffer

    def _filter(self, data):
        if self._filters:
            for filter in self._filters:
                data = filter(data)
        return data


class TextBufferContext(BaseBufferContext):

    def _make_buffer(self):
        return StringIO()


class BinaryBufferContext(BaseBufferContext):

    def _make_buffer(self):
        return BytesIO()


class TextEqualContext(TextBufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            with open(self._path, 'r') as input:
                target = input.read()
                result = self._filter(self._buffer.getvalue())
                if result != target:
                    with NamedTemporaryFile(delete=False) as f:
                        f.write(result.encode())
                        self._log.info('Wrote copy of result to %s' % f.name)
                        self._log.info('Comparing with %s' % self._path)
                        self._log.info('diff %s %s' % (f.name, self._path))
                self._test.assertEqual(result, target)


class BinaryEqualContext(BinaryBufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            with open(self._path, 'rb') as input:
                target = input.read()
                result = self._filter(self._buffer.getvalue())
                if result != target:
                    with NamedTemporaryFile(delete=False) as f:
                        f.write(result)
                        self._log.info('Wrote copy of result to %s' % f.name)
                        self._log.info('Comparing with %s' % self._path)
                        self._log.info('cmp -l %s %s' % (f.name, self._path))
                self._test.assertEqual(result, target)


class TextDumpContext(TextBufferContext):

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._log.warning('Error writing %s' % self._path)
        else:
            makedirs(dirname(self._path), exist_ok=True)
            with open(self._path, 'w') as output:
                output.write(self._filter(self._buffer.getvalue()))
            self._log.info('Wrote data to "%s"' % self._path)


class BinaryDumpContext(BinaryBufferContext):

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._log.warning('Error writing %s' % self._path)
        else:
            makedirs(dirname(self._path), exist_ok=True)
            with open(self._path, 'wb') as output:
                output.write(self._buffer.getvalue())
            self._log.info('Wrote data to "%s"' % self._path)


class CSVEqualContext(TextBufferContext):

    def __init__(self, log, path, filters, test):
        super().__init__(log, path, filters)
        self._test = test

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            with open(self._path, 'r') as them_in:
                them_reader = self._filter(reader(them_in))
                next(them_reader)  # drop titles
                us_data = self._buffer.getvalue()
                us_reader = self._filter(reader(us_data.splitlines()))
                for row, (us_row, them_row) in enumerate(zip_longest(us_reader, them_reader)):
                    self.compare_rows(row, us_row, them_row, us_data)

    def build_dict(self, row):
        return dict((name, (value, units)) for name, value, units in grouper(row, 3))

    def compare_rows(self, row, us_row, them_row, us_data):
        if us_row[0] == 'CompressedTimestamp': us_row[0] = 'Data'
        self._test.assertEqual(us_row[:3], them_row[:3], 'Row %d header' % row)
        us_dict = self.build_dict(us_row[3:])
        them_dict = self.build_dict(them_row[3:])
        keys = set(us_dict.keys()).union(them_dict.keys())
        for key in keys:
            self.compare_key(key, us_dict, them_dict, row, us_data)

    def compare_key(self, key, us_dict, them_dict, row, us_data):
        if key and key != 'unknown':
            us_value, us_units = us_dict.get(key, ('', ''))
            them_value, them_units = them_dict.get(key, ('', ''))
            try:
                if us_value != 'COMPOSITE':
                    self._test.assertEqual(self.fix_value(us_value), self.fix_value(them_value),
                                           'Value for %s row %d' % (key, row))
                    if us_value:  # avoid too many errors
                        self._test.assertEqual(us_units, them_units, 'Units for %s row %d' % (key, row))
            except Exception:
                self.dump(row, us_data)
                raise

    def fix_value(self, value):
        if value:
            if value.endswith('.0'): value = value[:-2]
            if value == 'False': value = '0'
            if value == 'True': value = '1'
        return value

    def dump(self, row, us_data):
        with NamedTemporaryFile(delete=False) as f:
            f.write(us_data.encode())
            self._log.info('Wrote copy of CSV to %s' % f.name)
            self._log.info('Comparing with %s' % self._path)
            self._log.info('head -n %d %s | tail -n 1; head -n %d %s | tail -n 1' %
                           (row+2, f.name, row+2, self._path))


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
            return TextEqualContext(log, path, filters, self)
        else:
            log.warning('File "%s" does not exist; will generate rather than check' % path)
            return TextDumpContext(log, path, filters)

    def assertBinaryMatch(self, path, log=None, filters=None):
        log = self._resolve_log(log)
        if exists(path):
            return BinaryEqualContext(log, path, filters, self)
        else:
            log.warning('File "%s" does not exist; will generate rather than check' % path)
            return BinaryDumpContext(log, path, filters)

    def assertCSVMatch(self, path, log=None, filters=None):
        log = self._resolve_log(log)
        if exists(path):
            return CSVEqualContext(log, path, filters, self)
        else:
            # the CSV file should have been generated using the SDK (dev/build-csv.sh)
            raise Exception('Could not open %s' % path)
