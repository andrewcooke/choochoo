from struct import unpack

from choochoo.fit.profile import LITTLE, BIG


def decode(log, path, messages):
    with open(path, 'rb') as input:
        data = input.read()
    offset = check_crc(log, data, messages)


CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
       0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def check_crc(log, data, messages):
    header = messages.profile_to_message('HEADER')
    (offset, message) = header.raw_to_internal(data, endian=LITTLE)
    log.debug('Header: %s' % message)
    checksum = 0
    for byte in data[offset:-2]:
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[byte & 0xf]
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[(byte >> 4) & 0xf]
    reference = unpack('<H', data[-2:])[0]
    if checksum != reference:
        raise Exception('Bad checksum (%04x / %04x)' % (checksum, reference))
    return offset
