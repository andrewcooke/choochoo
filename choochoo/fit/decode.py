
from choochoo.fit.profile import LITTLE, BIG


def decode(log, path, messages):
    with open(path, 'rb') as input:
        data = input.read()
    check_crc(log, data, messages)


def check_crc(log, data, messages):
    header = messages.profile_to_message('HEADER')
    (offset, message) = header.raw_to_internal(data, endian=LITTLE)
    print(message)
