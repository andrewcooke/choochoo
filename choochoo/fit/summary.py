
from collections import Counter

from .decode import parse_all
from .profile import chain, no_nulls, fix_degrees, append_units
from ..args import PATH
from ..log import make_log


def dump_fit(args, profile_path=None):
    log = make_log(args)
    fit_path = args.file(PATH, 0)
    summarize(log, fit_path, profile_path=profile_path)


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
            record = record.as_dict(filter=chain(append_units, fix_degrees, no_nulls))
            print(record.name)
            pprint_dict_with_tabs(record.data)
            print()


def pprint_as_tuples(records):
    # todo - save dicts for titles
    records = [record.as_values(filter=chain(append_units, fix_degrees, no_nulls))
               for record in records if record.name[0].islower]


def pprint_dict_with_tabs(dict, indent=2, tab=4, width=79):
    line = ' ' * indent
    first = True
    for name, value in sorted(dict.items()):
        chunk = '%s: %s' % (name, value)
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
