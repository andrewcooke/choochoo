
from abc import abstractmethod

from ..pipeline import DbPipeline
from ...fit.format.read import filtered_records
from ...fit.profile.profile import read_fit
from ...lib.date import to_time
from ...lib.io import for_modified_files


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class Importer(DbPipeline):
    '''
    Base class for importing from a files that have been modified.
    '''

    def _paths(self):
        return self._assert_karg('paths', default=tuple())

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
