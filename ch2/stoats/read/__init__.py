
from abc import abstractmethod
from logging import getLogger
from sys import exc_info
from traceback import format_tb

from ..pipeline import DbPipeline, MultiProcPipeline
from ...commands.args import ACTIVITIES, WORKER, mm, FAST
from ...fit.format.read import filtered_records
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...lib.io import for_modified_files, filter_modified_files, update_scan

log = getLogger(__name__)


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class Importer(DbPipeline):
    '''
    Base class for importing from a files that have been modified.
    '''

    def _paths(self):
        return self._karg('paths', default=tuple())

    def _import_all(self):
        with self._db.session_context() as s:
            for_modified_files(self._log, s, self._paths(), self._callback(), self, force=self._force())

    def _callback(self):
        def callback(file):
            self._log.debug('Scanning %s' % file)
            with self._db.session_context() as s:
                try:
                    self._import_path(s, file)
                    return True
                except AbortImport as e:
                    self._log.debug('Aborted %s' % file)
                    return isinstance(e, AbortImportButMarkScanned)
        return callback

    @abstractmethod
    def _import_path(self, s, path):
        pass


class FitImporter(Importer):
    '''
    Extend Importer with utility methods related to FIT files.
    '''

    def _load_fit_file(self, path, *options):
        types, messages, records = filtered_records(self._log, read_fit(self._log, path))
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
            self._log.debug(f'No {names} entry(s) in {path}')
            raise AbortImportButMarkScanned()


class MultiProcFitReader(MultiProcPipeline):

    def __init__(self, *args, paths=None, **kargs):
        self.paths = paths
        super().__init__(*args, **kargs)

    def _base_command(self):
        return f'{{ch2}} -v0 -l {{log}} {ACTIVITIES} {mm(WORKER)} {self.id} {mm(FAST)}'

    def _args(self, missing, start, finish):
        paths = ' '.join(repr(path) for path in missing[start:finish+1])  # quote names
        log.info(f'Starting worker for {missing[start]} - {missing[finish]}')
        return paths

    def _delete(self, s):
        pass  # we don't have anything to delete

    def _missing(self, s):
        return filter_modified_files(s, self.paths, self.owner_out, self.force)

    def _run_one(self, s, path):
        try:
            self._read(s, path)
            update_scan(s, path, self.owner_out)
        except AbortImportButMarkScanned as e:
            log.warning(f'Could not process {path} ({e}) (scanned)')
            update_scan(s, path, self.owner_out)
        except Exception as e:
            log.warning(f'Could not process {path} ({e}) (ignored)')
            log.debug('\n' + ''.join(format_tb(exc_info()[2])))

    @abstractmethod
    def _read(self, s, path):
        raise NotImplementedError()

    def _load_fit_file(self, path, *options):
        types, messages, records = filtered_records(log, read_fit(log, path))
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
