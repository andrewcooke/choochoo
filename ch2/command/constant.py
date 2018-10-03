
from sqlalchemy.sql.functions import count

from ..command.args import DATE, NAME, VALUE, DELETE, FORCE, mm, COMMAND, CONSTANT, SET
from ..squeal.database import Database
from ..squeal.tables.constant import Constant, ConstantJournal
from ..squeal.tables.source import Source
from ..squeal.tables.statistic import StatisticJournal, Statistic


def constant(args, log):
    '''
# constant

    ch2 constant [name [date]]

Lists constants to stdout.

    ch2 constant --set name [date] value

Defines a new entry.  If date is omitted a single value is used for all time.

    ch2 constant --delete name [date]

Deletes an entry.

Activity names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and FTHR.Bike, for example.
In such a case "entry" in the descriptions above may refer to multiple entries.
    '''
    name, date, value, set, delete, force = args[NAME], args[DATE], args[VALUE], args[SET], args[DELETE], args[FORCE]
    db = Database(args, log)
    with db.session_context() as s:
        if name:
            constants = Constant.lookup_like(log, s, name)
            if not constants:
                raise Exception('Name "%s" matched no entries (see `%s %s`)' % (name, COMMAND, CONSTANT))
        else:
            constants = []
        if set:
            # date is the optional entry for set
            if date and not value:
                date, value = None, date
            if not name or not value:
                raise Exception('%s requires name and value' % mm(SET))
            set_constants(log, s, constants, date, value, force)
        elif delete:
            if not name:
                raise Exception('%s requires at least a name' % mm(DELETE))
            if value:
                raise Exception('Do not provide a value when deleting Constants')
            if not date and not force:
                raise Exception('Use %s to delete all entries for a Constant' % mm(FORCE))
            delete_constants(log, s, constants, date)
        else:
            if value:
                raise Exception('Do not provide a value when printing Constants')
            print_constants(log, s, constants, name, date)


def set_constants(log, s, constants, date, value, force):
    if not date:
        log.info('Checking any previous values')
        journals = []
        for constant in constants:
            journals += s.query(ConstantJournal).join(StatisticJournal, Statistic, Constant). \
                filter(Constant.id == constant.id).all()
        if journals:
            log.info('Need to delete %d ConstantJournal entries' % len(journals))
            if not force:
                raise Exception('Use %s to confirm deletion of prior values' % mm(FORCE))
            for journal in journals:
                s.delete(journal)
        date = '1970-01-01'
    for constant in constants:
        journal = ConstantJournal(time=date)
        s.add(journal)
        StatisticJournal.add(log, s,
                             constant.statistic.name, constant.statistic.units, constant.statistic.summary,
                             Constant, constant.statistic.constraint, journal, value, constant.type)
        log.info('Added value %s at %s for %s' % (value, date, constant.name))
    log.warn('You may want to (re-)calculate statistics')


def delete_constants(log, s, constants, date):
    if date:
        for constant in constants:
            for repeat in range(2):
                journal = s.query(ConstantJournal).join(StatisticJournal, Statistic, Constant). \
                    filter(Constant.id == constant.id,
                           ConstantJournal.time == date).one_or_none()
                if repeat:
                    log.info('Deleting %s on %s' % (constant.name, journal.time))
                    s.delete(journal)
                else:
                    if not journal:
                        raise Exception('No entry for %s on %s' % (constant.name, date))
    else:
        for constant in constants:
            for journal in s.query(ConstantJournal).join(StatisticJournal, Statistic, Constant). \
                    filter(Constant.id == constant.id).order_by(ConstantJournal.time).all():
                log.info('Deleting %s on %s' % (constant.name, journal.time))
                s.delete(journal)


def print_constants(log, s, constants, name, date):
    if not constants:
        constants = s.query(Constant).order_by(Constant.name).all()
        if not constants:
            raise Exception('No Constants defined - configure system')
    for constant in constants:
        if not date:
            print()
            print('%s: %s' % (constant.name,
                              constant.statistic.description if constant.statistic.description else '[no description]'))
            if name:  # only print values if we're not listing all
                found = False
                for journal in s.query(StatisticJournal).join(ConstantJournal, Statistic, Constant). \
                        filter(Constant.id == constant.id).order_by(ConstantJournal.time).all():
                    print('%s: %s' % (journal.time, journal.value))
                    found = True
                if not found:
                    log.warn('No values found for %s' % constant.name)
        else:
            journal = ConstantJournal.lookup_statistic_journal(log, s, constant.name,
                                                               constant.statistic.constraint, date)
            if journal:
                print('%s %s %s' % (constant.name, journal.source.time, journal.value))
            else:
                log.warn('No values found for %s' % constant.name)

