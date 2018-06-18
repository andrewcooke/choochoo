
from sqlite3 import connect, Row

from .args import DATABASE


class Database:

    def __init__(self, args, log):
        path = args.file(DATABASE)
        log.info('Using database at %s' % path)
        self.db = connect(path, isolation_level=None)
        self.db.row_factory = Row
        self._create_tables()

    def _create_tables(self):
        self.db.executescript('''

create table if not exists diary (
  ordinal integer primary key,
  notes text not null,
  rest_hr integer not null,
  sleep integer not null,
  mood integer not null,
  weather text not null
);

create table if not exists injury (
  id integer primary key,
  start integer,
  finish integer,
  title text
);

create table if not exists injury_diary (
  ordinal integer not null,
  injury integer not null references injury(id),
  pain_avg integer not null,
  pain_peak integer not null,
  notes text not null,
  primary key (ordinal, injury)
) without rowid;

''')
