
from abc import abstractmethod
from logging import getLogger

from ..pipeline import MultiProcPipeline
from ...fit.format.read import filtered_records
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...lib.io import filter_modified_files, update_scan
from ...lib.log import log_current_exception

log = getLogger(__name__)


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class MultiProcFitReader(MultiProcPipeline):

    def __init__(self, *args, paths=None, **kargs):
        self.paths = paths
        super().__init__(*args, **kargs)

    def _args(self, missing, start, finish):
        paths = ' '.join(repr(path) for path in missing[start:finish+1])  # quote names
        log.info(f'Starting worker for {missing[start]} - {missing[finish]}')
        return paths

    def _delete(self, s):
        pass  # we delete on load

    def _missing(self, s):
        return filter_modified_files(s, self.paths, self.owner_out, self.force)

    def _run_one(self, s, path):
        try:
            self._read(s, path)
            update_scan(s, path, self.owner_out)
        except AbortImportButMarkScanned as e:
            log.warning(f'Could not process {path} (scanned)')
            log_current_exception()
            update_scan(s, path, self.owner_out)
        except Exception as e:
            log.warning(f'Could not process {path} (ignored)')
            log_current_exception()

    @abstractmethod
    def _read(self, s, path):
        raise NotImplementedError()

    def _load_fit_file(self, path, *options):
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
