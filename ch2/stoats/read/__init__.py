
from abc import abstractmethod
from logging import getLogger

from ..pipeline import MultiProcPipeline, UniProcPipeline, LoaderMixin
from ...fit.format.read import filtered_records
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...lib.io import filter_modified_files, update_scan
from ...lib.log import log_current_exception
from ...squeal import Timestamp

log = getLogger(__name__)


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class FitReaderMixin(LoaderMixin):

    def __init__(self, *args, paths=None, **kargs):
        self.paths = paths
        super().__init__(*args, **kargs)

    def _delete(self, s):
        # forcing does two things:
        # first, it by-passes the checks on last-scan date and duplicates
        # second, we delete any overlapping activities on load (when we know the times)
        # (without force, overlapping activities trigger an error)
        pass

    def _missing(self, s):
        return filter_modified_files(s, self.paths, self.owner_out, self.force)

    def _run_one(self, s, path):
        try:
            self._read(s, path)
            update_scan(s, path, self.owner_out)
        except AbortImportButMarkScanned as e:
            log.warning(f'Could not process {path} (scanned)')
            # log_current_exception()
            update_scan(s, path, self.owner_out)
        except Exception as e:
            log.warning(f'Could not process {path} (ignored)')
            log_current_exception()

    def _read(self, s, path):
        key, data = self._read_data(s, path)
        s.commit()
        with Timestamp(owner=self.owner_out, key=key).on_success(log, s):
            loader = self._get_loader(s)
            self._load_data(s, loader, data)
            loader.load()

    def _read_fit_file(self, path, *options):
        types, messages, records = filtered_records(read_fit(log, path))
        return [record.as_dict(*options)
                for _, _, record in sorted(records,
                                           key=lambda r: r[2].timestamp if r[2].timestamp else to_time(0.0))]

    def _first(self, path, records, *names):
        return self.__assert_contained(path, records, names, 0)

    def _last(self, path, records, *names):
        return self.__assert_contained(path, records, names, -1)

    def __assert_contained(self, path, records, names, index):
        try:
            return [record for record in records if record.name in names][index]
        except IndexError:
            log.debug(f'No {names} entry(s) in {path}')
            raise AbortImportButMarkScanned()

    @abstractmethod
    def _read_data(self, s, path):
        raise NotImplementedError()

    @abstractmethod
    def _load_data(self, s, loader, data):
        raise NotImplementedError()


class MultiProcFitReader(FitReaderMixin, MultiProcPipeline):

    def _args(self, missing, start, finish):
        paths = ' '.join(repr(path) for path in missing[start:finish+1])  # quote names
        log.info(f'Starting worker for {missing[start]} - {missing[finish]}')
        return paths


class UniProcFitReader(FitReaderMixin, UniProcPipeline):

    def _base_command(self):
        raise Exception('UniProc does not support workers')

    def _args(self, missing, start, finish):
        raise Exception('UniProc does not support workers')
