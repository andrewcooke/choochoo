
from collections import Counter

from .decode import Tokenizer, pipeline, instances, everything, drop, exhaust, load, TimedMsg, DataMsg, \
    expand_as_dict, collect_as_tuples, collect_as_list, to_degrees, delete_undefined_values, clean_unknown_messages, \
    clean_empty_messages, clean_unknown_fields, clean_fields
from ..args import PATH
from ..log import make_log


def dump_fit(args):
    log = make_log(args)
    fit_path = args.file(PATH, 0)
    dump(log, fit_path, '/home/andrew/Downloads/FitSDKRelease_20.67.00/Profile.xlsx')


def dump(log, fit_path, profile_path=None):
    log.info('Reading from %s' % fit_path)
    summarize(log, fit_path, profile_path=profile_path)


def summarize(log, fit_path, profile_path=None):
    data, types, messages, header = load(log, fit_path, profile_path=profile_path)
    tokenizer = Tokenizer(log, data, types, messages)
    counts = Counter()
    exhaust(pipeline(tokenizer,
                     [(everything, count_message_number(counts)),
                      (everything, drop)
                      ]))
    small, large = partition(counts)
    log.debug('Small messages: %s' % small)
    log.debug('Large messages: %s' % large)
    tokenizer = Tokenizer(log, data, types, messages)
    timed, data = {}, [header]
    exhaust(pipeline(tokenizer,
                     [(messages_in(small), expand_as_dict(log)),
                      (instances(dict), to_degrees(log)),
                      (instances(dict), clean_unknown_messages(log)),
                      (instances(dict), delete_undefined_values(log)),
                      (instances(dict), clean_unknown_fields(log)),
                      (instances(dict), clean_fields(log, ['TIMESTAMP'])),
                      (instances(dict), clean_empty_messages(log)),
                      (instances(dict), collect_as_list(log, data)),
                      (messages_in(large), collect_as_tuples(log, timed))
                      ]))
    print()
    pprint_dicts(data)
    pprint_tuples(timed)


def count_message_number(counts):
    def count(msg):
        counts[msg.definition.message.number] += 1
    return count


def messages_in(group):
    def test(value):
        return (isinstance(value, DataMsg) or isinstance(value, TimedMsg)) and \
               value.definition.message.number in group
    return test


def partition(counts, threshold=3):
    small = set(number for number, count in counts.items() if count <= threshold)
    large = set(number for number, count in counts.items() if count > threshold)
    return small, large


def pprint_dicts(data):
    for dict in data:
        print(dict['MESSAGE'])
        del dict['MESSAGE']
        pprint_dict_with_tabs(dict)
        print()


def pprint_tuples(timed):
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
