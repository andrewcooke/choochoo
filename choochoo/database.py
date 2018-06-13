
from sqlite3 import connect

from .args import DATABASE


class Database:

    def __init__(self, args):
        self.db = connect(args.file(DATABASE))
        self._create_tables()

    @staticmethod
    def null_to_text(text):
        return text if text else ''

    def _create_tables(self):
        self.db.execute('''create table if not exists diary (
                             ordinal integer primary key,
                             notes text not null
)''')
