
from logging import getLogger

from ..commands.args import DATE, NAME, VALUE, FORCE, COMMAND, CONSTANTS, SET, SUB_COMMAND, ADD, \
    SHOW, REMOVE, DESCRIPTION, SINGLE, VALIDATE, UNSET, LIST
from ..common.args import mm
from ..common.md import Markdown
from ..sql import ActivityGroup
from ..sql.tables.constant import Constant, ValidateNamedTuple
from ..sql.tables.statistic import StatisticJournal, StatisticName, StatisticJournalType
from ..sql.types import lookup_cls
from ..sql.utils import add

log = getLogger(__name__)


def constants(config):
    '''
## constants

    > ch2 constants list

Lists constant names on stdout.

    > ch2 constants show [NAME [DATE]]

Shows constant names, descriptions, and values (if NAME is given) on stdout.

    > ch2 constants add NAME

Defines a new constant.

    > ch2 constants set NAME VALUE [DATE]

Adds an entry for the constant.  If date is omitted a single value is used for all time
(so any previously defined values are deleted).

Note that adding / removing constants (ie their names) is separate from setting / deleting entries (ie their values).

    > ch2 constants unset NAME [DATE]

Deletes an entry.

    > ch2 constants remove NAME

Remove a constant (the associated entries must have been deleted first).

### Names

A constant name is a token (lower case letters, digits and underscores) optionally followed by a colon and
the name of an activity group.

Names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and FTHR.Bike, for example.
In such a case "entry" in the descriptions above may refer to multiple entries.
    '''
    args = config.args
    cmd = args[SUB_COMMAND]
    name = None if cmd == LIST else args[NAME]
    with config.db.session_context() as s:
        if cmd == ADD:
            add_constant(s, name, description=args[DESCRIPTION], single=args[SINGLE], validate=args[VALIDATE])
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
                date = None if cmd == LIST else args[DATE]
                if cmd == SET:
                    set_constants(s, constants, date, args[VALUE], args[FORCE])
                elif cmd == UNSET:
                    if not date and not args[FORCE]:
                        raise Exception(f'Use {mm(FORCE)} to delete all entries for a Constant')
                    delete_constants(s, constants, date)
                elif cmd in (SHOW, LIST):
                    print_constants(s, constants, name, date, names_only=(cmd == LIST))


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


def add_constant(s, name, description=None, single=False, validate=None):
    if Constant.from_name(s, name, none=True):
        raise Exception(f'Constant {name} already exists')
    if ':' in name:
        activity_group = ActivityGroup.from_name(s, name.split(':', 1)[1], none=True)
        if activity_group:
            raise Exception(f'Activity group does not exist for {name}')
    else:
        activity_group = None
    validate_cls, validate_args, validate_kargs = None, [], {}
    if validate:
        lookup_cls(validate)
        validate_cls, validate_kargs = ValidateNamedTuple, {'tuple_cls': validate}
    statistic_name = StatisticName.add_if_missing(s, name, StatisticJournalType.TEXT, None, None,
                                                  Constant, description=description)
    add(s, Constant(statistic_name=statistic_name, name=name, single=single, activity_group=activity_group,
                    validate_cls=validate_cls, validate_args=validate_args, validate_kargs=validate_kargs))
    log.info(f'Added {name}')


def set_constants(s, constants, date, value, force):
    if not date:
        log.info('Checking any previous values')
        journals = []
        for constant in constants:
            journals += journal_for_constant(s, constant)
        if journals:
            log.info(f'Need to delete {len(journals)} constant values')
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
                journal = journal_join_constant(s, constant).filter(StatisticJournal.time == date).one_or_none()
                if repeat:
                    log.info(f'Deleting {constant.name} on {journal.time}')
                    s.delete(journal)
                else:
                    if not journal:
                        raise Exception(f'No entry for {constant.name} on {date}')
    else:
        for constant in constants:
            for journal in journal_for_constant(s, constant):
                log.info(f'Deleting {constant.name} on {journal.time}')
                s.delete(journal)


def print_constants(s, constants, name, date, names_only=False):
    if not constants:
        constants = s.query(Constant).order_by(Constant.name).all()
        if not constants:
            raise Exception('No Constants defined - configure system')
    print()
    for constant in constants:
        if not date:
            print(f'{constant.name}')
            if not names_only:
                description = constant.statistic_name.description \
                    if constant.statistic_name.description else '[no description]'
                Markdown().print(description)
                if name:  # only print values if we're not listing all
                    found = False
                    # need to be epxlicit in joins because there's more than one way all can connect
                    # (since constant also references statistic name)
                    for journal in journal_for_constant(s, constant):
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
                # note - we do not remove the statistic name since it could be shared across multiple constants
                # for different activity groups (but we have ensured no journal entries exist)
                s.query(Constant).filter(Constant.id == constant.id).delete()
            else:
                if journal_for_constant(s, constant):
                    raise Exception(f'Values still defined for {constant.name}')


def journal_join_constant(s, constant):
    # need to be explicit in joins because there's more than one way all can connect
    # (since constant also references statistic name)
    return s.query(StatisticJournal). \
            join(StatisticName, StatisticName.id == StatisticJournal.statistic_name_id). \
            join(Constant, Constant.id == StatisticJournal.source_id). \
            filter(Constant.id == constant.id)


def journal_for_constant(s, constant):
    return journal_join_constant(s, constant).order_by(StatisticJournal.time).all()
