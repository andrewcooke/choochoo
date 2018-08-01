
from collections import Counter

from .decode import parse_all
from .profile import chain, no_nulls, fix_degrees
from ..args import PATH
from ..log import make_log


def dump_fit(args):
    log = make_log(args)
    fit_path = args.file(PATH, 0)
    summarize(log, fit_path, '/home/andrew/Downloads/FitSDKRelease_20.67.00/Profile.xlsx')


def summarize(log, fit_path, profile_path=None):
    records = list(parse_all(log, fit_path, profile_path=profile_path))
    counts = Counter(record.name for record in records)
    small, large = partition(records, counts)
    print()
    pprint_as_dicts(small)
    pprint_as_tuples(large)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.name] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records):
    for record in records:
        if record.name[0].islower():
            record = record.as_dict_with_units(filter=chain(no_nulls, fix_degrees))
            print(record.name)
            pprint_dict_with_tabs(record.data)
            print()


def pprint_as_tuples(timed):
    # print(timed)
    pass


def pprint_dict_with_tabs(dict, indent=2, tab=4, width=79):
    line = ' ' * indent
    first = True
    for name, (value, units) in sorted(dict.items()):
        chunk = '%s: %s%s' % (name, value, '' if units is None else units)
        if not first:
            line += ','
        l_old = len(line)
        if l_old > indent:
            l_new = (1 + (l_old - indent + 1) // tab) * tab + indent
            if l_new + len(chunk) > width:
                print(line)
                line = ' ' * indent + chunk
            else:
                line += ' ' * (l_new - l_old) + chunk
        else:
            line += chunk
        first = False
    if len(line) > indent:
        print(line)
