
from sqlite3 import connect, Row

from .args import DATABASE


class Database:

    def __init__(self, args, log):
        self._log = log
        path = args.file(DATABASE)
        self._log.info('Using database at %s' % path)
        self.db = connect(path, isolation_level=None)
        self.db.row_factory = Row
        self._create_tables()

    def execute(self, cmd, args):
        self._log.debug('%s / %s' % (cmd, args))
        return self.db.execute(cmd, args)

    def _create_tables(self):
        self.db.executescript('''

create table if not exists diary (
  ordinal integer primary key,
  notes text not null,
  rest_hr integer,
  sleep integer,
  mood integer,
  weather text not null
);

create table if not exists injury (
  id integer primary key,
  start integer,
  finish integer,
  title text,
  description text
);

create table if not exists injury_diary (
  ordinal integer not null,
  injury integer not null references injury(id),
  pain_avg integer,
  pain_peak integer,
  pain_freq integer,
  notes text not null,
  primary key (ordinal, injury)
) without rowid;

create table if not exists aim (
  id integer primary key,
  start integer,
  finish integer,
  title text,
  description text
);

create table if not exists aim_diary (
  ordinal integer not null,
  aim integer not null references aim(id),
  notes text not null,
  primary key (ordinal, aim)
) without rowid;

''')
