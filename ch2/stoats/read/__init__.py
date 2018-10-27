
from abc import abstractmethod

from ch2.lib.io import for_modified_files


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class Importer:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def _first(self, path, records, *names):
        try:
            return next(iter(record for record in records if record.name in names))
        except StopIteration:
            self._log.warn('No %s entry(s) in %s' % (str(names), path))
            raise AbortImportButMarkScanned()

    def _last(self, path, records, *names):
        save = None
        for record in records:
            if record.name in names:
                save = record
        if not save:
            self._log.warn('No %s entry(s) in %s' % (str(names), path))
            raise AbortImportButMarkScanned()
        return save

    def _run(self, paths, force=False, **kargs):
        with self._db.session_context() as s:
            for_modified_files(self._log, s, paths, self._callback(kargs), self, force=force)

    def _callback(self, kargs):
        def callback(file):
            self._log.info('Scanning %s' % file)
            with self._db.session_context() as s:
                try:
                    self._import(s, file, **kargs)
                    return True
                except AbortImport as e:
                    self._log.debug('Aborted %s' % file)
                    return isinstance(e, AbortImportButMarkScanned)
        return callback

    @abstractmethod
    def _import(self, s, path, **kargs):
        pass
