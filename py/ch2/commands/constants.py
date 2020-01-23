
from logging import getLogger

from ..commands.args import DATE, NAME, VALUE, DELETE, FORCE, mm, COMMAND, CONSTANTS, SET, SUB_COMMAND, ADD, \
    SHOW, REMOVE, CONSTRAINT, DESCRIPTION, SINGLE, VALIDATE
from ..sql.tables.constant import Constant, ValidateNamedTuple
from ..sql.tables.statistic import StatisticJournal, StatisticName, StatisticJournalType
from ..sql.types import lookup_cls
from ..sql.utils import add

log = getLogger(__name__)


def constants(args, system, db):
    '''
## constants

    > ch2 constants show [NAME [DATE]]

Lists constants to stdout.

    > ch2 constants set NAME VALUE [DATE]

Defines a new entry.  If date is omitted a single value is used for all time
(so any previously defined values are deleted)

    > ch2 constants delete NAME [DATE]

Deletes an entry.

Names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and FTHR.Bike, for example.
In such a case "entry" in the descriptions above may refer to multiple entries.
    '''
    name, cmd = args[NAME], args[SUB_COMMAND]
    with db.session_context() as s:
        if cmd == ADD:
            add_constant(s, name, constraint=args[CONSTRAINT], description=args[DESCRIPTION],
                         single=args[SINGLE], validate=args[VALIDATE])
        else:
            if name:
                constants = constants_like(s, name)
                if not constants:
                    raise Exception(f'Name "{name}" matched no entries (see `{COMMAND} {CONSTANTS}`)')
            else:
                constants = []
            if cmd == REMOVE:
                if len(constants) > 1 and not args[FORCE]:
                    raise Exception(f'Use {mm(FORCE)} to remove multiple constants')
                remove_constants(s, constants)
            else:
                date = args[DATE]
                if cmd == SET:
                    set_constants(s, constants, date, args[VALUE], args[FORCE])
                elif cmd == DELETE:
                    if not date and not args[FORCE]:
                        raise Exception(f'Use {mm(FORCE)} to delete all entries for a Constant')
                    delete_constants(s, constants, date)
                elif cmd == SHOW:
                    print_constants(s, constants, name, date)


def constants_like(s, name):
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


def add_constant(s, name, constraint=None, description=None, single=False, validate=None):
    if s.query(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == Constant,
                   StatisticName.constraint == constraint).one_or_none():
        raise Exception(f'Constant {name} (constraint {constraint}) already exists')
    validate_cls, validate_args, validate_kargs = None, [], {}
    if validate:
        lookup_cls(validate)
        validate_cls, validate_kargs = ValidateNamedTuple, {'tuple_cls': validate}
    statistic_name = add(s, StatisticName(name=name, owner=Constant, constraint=constraint,
                                          units=None, description=description,
                                          statistic_journal_type=StatisticJournalType.TEXT))
    add(s, Constant(statistic_name=statistic_name, name=name, single=single,
                    validate_cls=validate_cls, validate_args=validate_args, validate_kargs=validate_kargs))
    log.info(f'Added {name}')


def set_constants(s, constants, date, value, force):
    if not date:
        log.info('Checking any previous values')
        journals = []
        for constant in constants:
            journals += s.query(StatisticJournal).join(StatisticName, Constant). \
                filter(Constant.id == constant.id).all()
        if journals:
            log.info(f'Need to delete {len(journals)} ConstantJournal entries')
            if not force:
                raise Exception(f'Use {mm(FORCE)} to confirm deletion of prior values')
            for journal in journals:
                s.delete(journal)
    for constant in constants:
        constant.add_value(s, value, date=date)
        log.info(f'Added value {value} at {date} for {constant.name}')
    log.warning('You may want to (re-)calculate statistics')


def delete_constants(s, constants, date):
    if date:
        for constant in constants:
            for repeat in range(2):
                journal = s.query(StatisticJournal).join(StatisticName, Constant). \
                    filter(Constant.id == constant.id,
                           StatisticJournal.time == date).one_or_none()
                if repeat:
                    log.info(f'Deleting {constant.name} on {journal.time}')
                    s.delete(journal)
                else:
                    if not journal:
                        raise Exception(f'No entry for {constant.name} on {date}')
    else:
        for constant in constants:
            for journal in s.query(StatisticJournal).join(StatisticName, Constant). \
                    filter(Constant.id == constant.id).order_by(StatisticJournal.time).all():
                log.info(f'Deleting {constant.name} on {journal.time}')
                s.delete(journal)


def print_constants(s, constants, name, date):
    if not constants:
        constants = s.query(Constant).order_by(Constant.name).all()
        if not constants:
            raise Exception('No Constants defined - configure system')
    print()
    for constant in constants:
        if not date:
            description = constant.statistic_name.description \
                if constant.statistic_name.description else '[no description]'
            print(f'{constant.name}: {description}')
            if name:  # only print values if we're not listing all
                found = False
                for journal in s.query(StatisticJournal).join(StatisticName, Constant). \
                        filter(Constant.id == constant.id).order_by(StatisticJournal.time).all():
                    print(f'{journal.time}: {journal.value}')
                    found = True
                if not found:
                    log.warning(f'No values found for {constant.name}')
            print()
        else:
            journal = constant.at(s, date=date)
            if journal:
                print(f'{constant.name} {journal.source.time} {journal.value}')
            else:
                log.warning(f'No values found for {constant.name}')


def remove_constants(s, constants):
    for do in (0, 1):
        for constant in constants:
            if do:
                log.warning(f'Deleting {constant.name}')
                s.query(StatisticName).filter(StatisticName.id == constant.statistic_name_id).delete()
                s.query(Constant).filter(Constant.id == constant.id).delete()
            else:
                if s.query(StatisticJournal). \
                        join(StatisticName, Constant). \
                        filter(Constant.id == constant.id).count():
                    raise Exception(f'Values still defined for {constant.name}')
