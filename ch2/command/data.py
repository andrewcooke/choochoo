
import pandas as pd

from ..data.database import Data
from .args import ACTIVITY_GROUPS, SUB_COMMAND, ACTIVITY_JOURNALS, GROUP, START, FINISH, STATISTIC_NAMES, NAMES, \
    STATISTIC_JOURNALS, OWNER, CONSTRAINT, SCHEDULE, SOURCE_ID, STATISTIC_QUARTILES, MONITOR_JOURNALS, PRINT, FORMAT, \
    CSV, DESCRIBE, MAX_COLUMNS, MAX_ROWS, WIDTH, MAX_COLWIDTH


def data(args, log, db):
    '''
## data

    > ch2 data COMMAND

Simple access to Pandas DataFrames - the same interface provided in Jupyter notebooks,
but accessed from the command line.

The format can be selected with --print (the default), --csv and --describe.

For full options see `ch2 data -h` and `ch2 data COMMAND -h`

### Examples

    > ch2 data --csv statistic-names

Will print details on all statistic names in CSV format.

    > ch2 data statistic-journals '%HR%' --constraint 'ActivityGroup "Bike"' --start 2018-01-01

Will print HR-related statistics from the start of 2018 for the given activity group.
    '''
    data = Data(log, db)

    if args[SUB_COMMAND] == ACTIVITY_GROUPS:
        frame = data.activity_groups()
    elif args[SUB_COMMAND] == ACTIVITY_JOURNALS:
        frame = data.activity_journals(args[GROUP], start=args[START], finish=args[FINISH])
    elif args[SUB_COMMAND] == STATISTIC_NAMES:
        frame = data.statistic_names(*args[NAMES])
    elif args[SUB_COMMAND] == STATISTIC_JOURNALS:
        frame = data.statistic_journals(*args[NAMES], start=args[START], finish=args[FINISH],
                                        owner=args[OWNER], constraint=args[CONSTRAINT],
                                        schedule=args[SCHEDULE], source_id=args[SOURCE_ID])
    elif args[SUB_COMMAND] == STATISTIC_QUARTILES:
        frame = data.statistic_quartiles(*args[NAMES], start=args[START], finish=args[FINISH],
                                         owner=args[OWNER], constraint=args[CONSTRAINT],
                                         schedule=args[SCHEDULE], source_id=args[SOURCE_ID])
    elif args[SUB_COMMAND] == MONITOR_JOURNALS:
        frame = data.monitor_journals()

    pd.options.display.max_columns = args[MAX_COLUMNS]
    if args[MAX_COLWIDTH] is not None: pd.options.display.max_colwidth = args[MAX_COLWIDTH]
    pd.options.display.max_rows = args[MAX_ROWS]
    pd.options.display.width = args[WIDTH]

    if args[FORMAT] == PRINT:
        print(frame)
    elif args[FORMAT] == CSV:
        print(frame.to_csv())
    elif args[FORMAT] == DESCRIBE:
        print(frame.describe(include='all'))
