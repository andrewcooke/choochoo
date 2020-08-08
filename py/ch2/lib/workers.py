from contextlib import contextmanager
from logging import getLogger
from os import getpid
from sys import argv

from math import floor

log = getLogger(__name__)


def command_root():
    try:
        with open(f'/proc/{getpid()}/cmdline', 'rb') as f:
            line = f.readline()

            def parse():
                word = bytearray()
                for char in line:
                    if char:
                        word.append(char)
                    else:
                        yield word.decode('utf8')
                        word = bytearray()

            words = list(parse())
            log.debug(f'Parsed /proc/{getpid()}/cmdline as {" ".join(words)}')
            if len(argv) > 1:
                i = words.index(argv[1])
                words = words[:i]
            ch2 = ' '.join(words)
            if 'unittest' in ch2:
                log.warning(f'Appear to be inside test runner: {ch2}')
                ch2 = 'python -m ch2'
            log.debug(f'Using command "{ch2}"')
            return ch2
    except:
        log.warning('Cannot read /proc so assuming that ch2 is started on the command line as "ch2"')
        return 'ch2'
