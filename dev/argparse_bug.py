
# https://bugs.python.org/issue26952

from argparse import ArgumentParser

def parser():

    parser = ArgumentParser(prog='name')
    subparsers = parser.add_subparsers()
    fit = subparsers.add_parser('fit')
    fit_limits = fit.add_mutually_exclusive_group()
    fit_records = fit_limits.add_argument_group()
    fit_records.add_argument('--limit-records')
    fit_bytes = fit_limits.add_argument_group()
    fit_bytes.add_argument('--limit--bytes')

    return parser

p = parser()
p.parse_args(['fit', '-h'])
