from abc import abstractmethod
from glob import iglob
from logging import getLogger
from os.path import join
from time import time

from ch2 import FatalException
from ch2.commands.args import base_system_path, PERMANENT
from ch2.fit.format.read import filtered_records
from ch2.lib import to_time, log_current_exception
from ch2.lib.io import modified_file_scans
from ch2.pipeline.pipeline import LoaderMixin, MultiProcPipeline
from ch2.sql import Timestamp

log = getLogger(__name__)


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class FitReaderMixin(LoaderMixin):

    def __init__(self, *args, paths=None, sub_dir=None, **kargs):
        self.paths = paths
        self.sub_dir = sub_dir
        super().__init__(*args, **kargs)

    def _delete(self, s):
        # forcing does two things:
        # first, it by-passes the checks on last-scan date and duplicates
        # second, we delete any overlapping activities on load (when we know the times)
        # (without force, overlapping activities trigger an error)
        pass

    def _expand_paths(self, s, paths):
        from ...commands.upload import DOT_FIT
        if paths: return paths
        data_dir = base_system_path(self.base, version=PERMANENT)
        if self.sub_dir:
            data_dir = join(data_dir, self.sub_dir)
        else:
            log.warning('No sub_dir defined - will scan entire tree')
        return iglob(join(data_dir, '**/*' + DOT_FIT), recursive=True)

    def _missing(self, s):
        return modified_file_scans(s, self._expand_paths(s, self.paths), self.owner_out, self.force)

    def _run_one(self, s, file_scan):
        try:
            self._read(s, file_scan)
            file_scan.last_scan = time()
        except AbortImportButMarkScanned as e:
            log.warning(f'Could not process {file_scan} (scanned)')
            # log_current_exception()
            file_scan.last_scan = time()
        except FatalException:
            raise
        except Exception as e:
            log.warning(f'Could not process {file_scan} (ignored)')
            log_current_exception()

    def _read(self, s, file_scan):
        source, data = self._read_data(s, file_scan)
        s.commit()
        with Timestamp(owner=self.owner_out, source=source).on_success(s):
            loader = self._get_loader(s)
            self._load_data(s, loader, data)
            loader.load()
        return loader  # returned so coverage can be accessed

    @staticmethod
    def read_fit_file(data, *options):
        types, messages, records = filtered_records(data)
        return [record.as_dict(*options)
                for _, _, record in sorted(records,
                                           key=lambda r: r[2].timestamp if r[2].timestamp else to_time(0.0))]

    @staticmethod
    def _first(path, records, *names):
        return FitReaderMixin.assert_contained(path, records, names, 0)

    @staticmethod
    def _last(path, records, *names):
        return FitReaderMixin.assert_contained(path, records, names, -1)

    @staticmethod
    def assert_contained(path, records, names, index):
        try:
            return [record for record in records if record.name in names][index]
        except IndexError:
            msg = f'No {names} entry(s) in {path}'
            log.debug(msg)
            raise AbortImportButMarkScanned(msg)

    @abstractmethod
    def _read_data(self, s, file_scan):
        raise NotImplementedError()

    @abstractmethod
    def _load_data(self, s, loader, data):
        raise NotImplementedError()


def quote(text):
    return '"' + text + '"'


class MultiProcFitReader(FitReaderMixin, MultiProcPipeline):

    def _args(self, missing, start, finish):
        paths = ' '.join(quote(file_scan.path) for file_scan in missing[start:finish+1])
        log.info(f'Starting worker for {missing[start]} - {missing[finish]}')
        return paths