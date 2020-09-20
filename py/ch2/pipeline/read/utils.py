from abc import abstractmethod
from glob import iglob
from logging import getLogger
from os.path import join

from ..pipeline import ProcessPipeline
from ... import FatalException
from ...commands.args import base_system_path, PERMANENT, BASE
from ...common.date import now
from ...common.log import log_current_exception
from ...fit.format.read import filtered_records
from ...lib import to_time
from ...lib.io import modified_file_scans
from ...sql import Timestamp, FileScan

log = getLogger(__name__)


class AbortImport(Exception):
    pass


class AbortImportButMarkScanned(AbortImport):
    pass


class ProcessFitReader(ProcessPipeline):

    def __init__(self, config, *args, sub_dir=None, **kargs):
        self.sub_dir = sub_dir
        super().__init__(config, *args, **kargs)

    def _all_paths(self):
        from ...commands.upload import DOT_FIT
        data_dir = base_system_path(self._config.args[BASE], version=PERMANENT)
        if self.sub_dir:
            data_dir = join(data_dir, self.sub_dir)
        else:
            log.warning('No sub_dir defined - will scan entire tree')
        return iglob(join(data_dir, '**/*' + DOT_FIT), recursive=True)

    def _missing(self, s):
        return [file_scan.path for file_scan in modified_file_scans(s, self._all_paths(), self.owner_out)]

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            file_scan = s.query(FileScan).filter(FileScan.path == missed).one()
            try:
                self._read(s, file_scan)
                file_scan.last_scan = now()
            except AbortImportButMarkScanned as e:
                log.warning(f'Could not process {file_scan} (scanned)')
                # log_current_exception()
                file_scan.last_scan = now()
            except FatalException:
                raise
            except Exception as e:
                log.warning(f'Could not process {file_scan} (ignored)')
                log_current_exception()

    def _read(self, s, file_scan):
        path = file_scan.path  # read this now so that on error we don't go back to database
        try:
            source, data = self._read_data(s, file_scan)
            with Timestamp(owner=self.owner_out, source=source).on_success(s):
                loader = self._get_loader(s, add_serial=True)
                self._load_data(s, loader, data)
                loader.load()
            return loader  # returned so coverage can be accessed
        except Exception as e:
            log.error(f'Error loading {path}: {e}')
            s.rollback()
            raise AbortImportButMarkScanned()

    @staticmethod
    def read_fit_file(data, *options):
        types, messages, records = filtered_records(data)
        return [record.as_dict(*options)
                for _, _, record in sorted(records,
                                           key=lambda r: r[2].timestamp if r[2].timestamp else to_time(0.0))]

    @staticmethod
    def _first(path, records, *names):
        return ProcessFitReader.assert_contained(path, records, names, 0)

    @staticmethod
    def _last(path, records, *names):
        return ProcessFitReader.assert_contained(path, records, names, -1)

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
