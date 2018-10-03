
from sqlalchemy.sql.functions import count

from ..lib.args import DATE, NAME, VALUE, DELETE, FORCE, mm, COMMAND, CONSTANT
from ..squeal.database import Database
from ..squeal.tables.constant import Constant, ConstantJournal
from ..squeal.tables.source import Source
from ..squeal.tables.statistic import StatisticJournal, Statistic


def constant(args, log):
    '''
# constant

    ch2 constant

Lists all constant names to stdout.

    ch2 constant name

Displays information on the given constant.

    ch2 constant name date

Displays the value for the constant at the given date.

    ch2 constant name date value

Defines a new entry.

    ch2 constant --delete name [date] [value]

Deletes an entry / entries.

Activity names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and FTHR.Bike, for example.
    '''
    name, date, value, delete, force = args[NAME], args[DATE], args[VALUE], args[DELETE], args[FORCE]
    db = Database(args, log)
    with db.session_context() as s:
        if name:
            constants = Constant.lookup_all(log, s, name)
            if not constants:
                raise Exception('Name "%s" matched no entries (see `%s %s`)' % (name, COMMAND, CONSTANT))
            if date:
                if delete:
                    delete_entry(log, s, constants, date, value, force)
                elif value:
                    set_entry(log, s, constants, date, value)
                else:
                    print_entry(log, s, constants, date)
            elif delete:
                delete_all(log, s, constants, force)
            else:
                print_description(log, s, constants)
        elif delete:
            raise Exception('Cannot delete all constants in a single command (provide name)')
        else:
            print_all(log, s)


def delete_entry(log, s, constants, date, value, force):
    journals = []
    for constant in constants:
        journals += s.query(StatisticJournal).join(ConstantJournal). \
            filter(StatisticJournal.statistic == constant.statistic,
                   ConstantJournal.time == date).all()
    if not journals:
        raise Exception('No values found at %s' % date)
    # two passes - check first
    for journal in journals:
        if value:
            if journal.value != journal.parse(value):
                raise Exception('Value to be deleted (%s) does not match value given (%s)' %
                                (journal.value, value))
        elif not force:
            raise Exception('Provide value or use %s' % mm(FORCE))
        for journal in journals:
            log.info('Deleting %s' % journal)
            s.delete(journal.source)
        log.warn('You may want to (re-)calculate statistics')


def set_entry(log, s, constants, date, value):
    for constant in constants:
        journal = ConstantJournal(time=date)
        s.add(journal)
        StatisticJournal.add(log, s,
                             constant.statistic.name, constant.statistic.units, constant.statistic.summary,
                             Constant, constant.statistic.constraint, journal, value, constant.type)
        log.info('Added value %s at %s for %s' % (value, date, constant.name))
    log.warn('You may want to (re-)calculate statistics')


def print_entry(log, s, constants, date):
    for constant in constants:
        journal = ConstantJournal.lookup(log, s, constant.statistic.name, date)
        if journal:
            print(journal.value)
        else:
            log.warn('No value found for %s at (or before) %s' % (constant.name, date))


def delete_all(log, s, constants, force):
    for constant in constants:
        n = s.query(count(StatisticJournal.id)). \
            filter(StatisticJournal.statistic == constant.statistic).scalar()
        if n:
            if not force:
                raise Exception('Confirm with %s' % mm(FORCE))
            for journal in s.query(StatisticJournal).join(ConstantJournal). \
                    filter(StatisticJournal.statistic == constant.statistic).all():
                log.info('Deleting %s' % journal)
                s.delete(journal.source)
            log.warn('You may want to (re-)calculate statistics')
        else:
            log.info('No entries to delete for %s' % constant.name)


def print_description(log, s, constants):
    for constant in constants:
        print()
        print('name: %s' % constant.name)
        if constant.statistic.description:
            print('description: %s' % constant.statistic.description)
        else:
            log.warn('No description for %s' % constant.statistic)
        found = False
        for journal in s.query(StatisticJournal).join(Source). \
                filter(StatisticJournal.statistic == constant.statistic). \
                order_by(Source.time).all():
            print('%s: %s' % (journal.time, journal.value))
            found = True
        if not found:
            log.warn('No values for %s' % constant)


def print_all(log, s):
    found  = False
    for constant in s.query(Constant).join(Statistic).order_by(Statistic.name).all():
        print(constant.name)
        found = True
    if not found:
        log.warn('No constants defined')

