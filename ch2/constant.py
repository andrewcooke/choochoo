from sqlalchemy import desc
from sqlalchemy.sql.functions import count

from .args import DATE, NAME, VALUE, DELETE, FORCE, mm
from .squeal.database import Database
from .squeal.tables.constant import Constant, ConstantJournal
from .squeal.tables.source import Source
from .squeal.tables.statistic import StatisticJournal, Statistic


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
    '''
    name, date, value, delete, force = args[NAME], args[DATE], args[VALUE], args[DELETE], args[FORCE]
    db = Database(args, log)
    with db.session_context() as s:
        if name:
            constant = Constant.lookup(log, s, name)
            if date:
                if delete:
                    delete_entry(log, s, constant, date, value, force)
                elif value:
                    set_entry(log, s, constant, date, value)
                else:
                    print_entry(log, s, constant, date)
            elif delete:
                delete_all(log, s, constant, force)
            else:
                print_description(log, s, constant)
        elif delete:
            raise Exception('Cannot delete all constants in a single command (provide name)')
        else:
            print_all(log, s)


def delete_entry(log, s, constant, date, value, force):
    journal = s.query(StatisticJournal).join(ConstantJournal). \
        filter(StatisticJournal.statistic == constant.statistic,
               ConstantJournal.time <= date). \
        order_by(desc(ConstantJournal.time)).limit(1).one_or_none()
    if journal:
        if value:
            if journal.value != journal.parse(value):
                raise Exception('Value to be deleted (%s) does not match value given (%s)' %
                                (journal.value, value))
        elif not force:
            raise Exception('Provide value or use %s' % mm(FORCE))
        log.info('Deleting value %s from %s' % (journal.value, journal.time))
        s.delete(journal.source)
    else:
        log.warn('No value found for %s at (or before) %s' % (constant.statistic.name, date))


def set_entry(log, s, constant, date, value):
    journal = ConstantJournal(time=date)
    s.add(journal)
    StatisticJournal.add(log, s,
                         constant.statistic.name, constant.statistic.units, constant.statistic.summary,
                         Constant, None, journal, value, constant.type)
    log.info('Added value %s at %s' % (value, date))


def print_entry(log, s, constant, date):
    journal = ConstantJournal.lookup(log, s, constant.statistic.name, date)
    if journal:
        print(journal.value)
    else:
        log.warn('No value found for %s at (or before) %s' % (constant.statistic.name, date))


def delete_all(log, s, constant, force):
    n = s.query(count(StatisticJournal.id)). \
        filter(StatisticJournal.statistic == constant.statistic).scalar()
    if n:
        if not force:
            raise Exception('Confirm with %s' % mm(FORCE))
        for journal in s.query(StatisticJournal).join(ConstantJournal). \
                filter(StatisticJournal.statistic == constant.statistic).all():
            log.info('Deleting value %s from %s' % (journal.value, journal.time))
            s.delete(journal.source)
    else:
        log.info('No entries to delete for %s' % constant.statistic.name)


def print_description(log, s, constant):
    print('name: %s' % constant.statistic.name)
    if constant.statistic.description:
        print('description: %s', constant.statistic.description)
    else:
        log.warn('No description for %s' % constant.statistic.name)
    found = False
    for journal in s.query(StatisticJournal).join(Source). \
            filter(StatisticJournal.statistic == constant.statistic). \
            order_by(Source.time).all():
        print('%s: %s' % (journal.time, journal.value))
        found = True
    if not found:
        log.warn('No values for %s' % constant.statistic.name)


def print_all(log, s):
    found  = False
    for constant in s.query(Constant).join(Statistic).order_by(Statistic.name).all():
        print(constant.statistic.name)
        found = True
    if not found:
        log.warn('No constants defined')

