from logging import getLogger

from ..commands.args import DATE, NAME, VALUE, DELETE, FORCE, mm, COMMAND, CONSTANTS, SET
from ..squeal.tables.constant import Constant
from ..squeal.tables.statistic import StatisticJournal, StatisticName

log = getLogger(__name__)


def constants(args, db):
    '''
## constants

    > ch2 constants [NAME [DATE]]

Lists constants to stdout.

    > ch2 constants --set NAME [DATE] VALUE

Defines a new entry.  If date is omitted a single value is used for all time
(so any previously defined values are deleted)

    > ch2 constants --delete NAME [DATE]

Deletes an entry.

Names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and FTHR.Bike, for example.
In such a case "entry" in the descriptions above may refer to multiple entries.
    '''
    name, date, value, set, delete, force = args[NAME], args[DATE], args[VALUE], args[SET], args[DELETE], args[FORCE]
    with db.session_context() as s:
        if name:
            constants = constants_like(log, s, name)
            if not constants:
                raise Exception('Name "%s" matched no entries (see `%s %s`)' % (name, COMMAND, CONSTANTS))
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


def constants_like(log, s, name):
    constants = s.query(Constant).filter(Constant.name.like(name)).order_by(Constant.name).all()
    if not constants:
        all_constants = s.query(Constant).all()
        if all_constants:
            log.info('Available constants:')
            for constants in all_constants:
                log.info('%s - %s' % (constants.statistic_name.name, constants.statistic_name.description))
        else:
            log.error('No constants defined - configure system correctly')
        raise Exception('Constant "%s" is not defined' % name)
    return constants


def set_constants(log, s, constants, date, value, force):
    if not date:
        log.info('Checking any previous values')
        journals = []
        for constant in constants:
            journals += s.query(StatisticJournal).join(StatisticName, Constant). \
                filter(Constant.id == constant.id).all()
        if journals:
            log.info('Need to delete %d ConstantJournal entries' % len(journals))
            if not force:
                raise Exception('Use %s to confirm deletion of prior values' % mm(FORCE))
            for journal in journals:
                s.delete(journal)
    for constant in constants:
        constant.add_value(s, value, date=date)
        log.info('Added value %s at %s for %s' % (value, date, constant.name))
    log.warning('You may want to (re-)calculate statistics')


def delete_constants(log, s, constants, date):
    if date:
        for constant in constants:
            for repeat in range(2):
                journal = s.query(StatisticJournal).join(StatisticName, Constant). \
                    filter(Constant.id == constant.id,
                           StatisticJournal.time == date).one_or_none()
                if repeat:
                    log.info('Deleting %s on %s' % (constant.name, journal.time))
                    s.delete(journal)
                else:
                    if not journal:
                        raise Exception('No entry for %s on %s' % (constant.name, date))
    else:
        for constant in constants:
            for journal in s.query(StatisticJournal).join(StatisticName, Constant). \
                    filter(Constant.id == constant.id).order_by(StatisticJournal.time).all():
                log.info('Deleting %s on %s' % (constant.name, journal.time))
                s.delete(journal)


def print_constants(log, s, constants, name, date):
    if not constants:
        constants = s.query(Constant).order_by(Constant.name).all()
        if not constants:
            raise Exception('No Constants defined - configure system')
    print()
    for constant in constants:
        if not date:
            print('%s: %s' % (constant.name,
                              constant.statistic_name.description
                              if constant.statistic_name.description else '[no description]'))
            if name:  # only print values if we're not listing all
                found = False
                for journal in s.query(StatisticJournal).join(StatisticName, Constant). \
                        filter(Constant.id == constant.id).order_by(StatisticJournal.time).all():
                    print('%s: %s' % (journal.time, journal.value))
                    found = True
                if not found:
                    log.warning('No values found for %s' % constant.name)
            print()
        else:
            journal = constant.at(s, date=date)
            if journal:
                print('%s %s %s' % (constant.name, journal.source.time, journal.value))
            else:
                log.warning('No values found for %s' % constant.name)

