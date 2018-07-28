
from struct import unpack

from choochoo.fit.profile import LITTLE, BIG, load_profile


def decode_all(log, path):
    data = read_path(path)
    log.debug('Read "%s"' % path)
    types, messages = load_profile(log)
    log.debug('Read profile')
    _offset, header = read_header(log, data, messages)
    log.debug('Header: %s' % header)
    stripped, checksum = strip_header_crc(data)
    log.debug('Checked length')
    check_crc(stripped, checksum)
    log.debug('Checked checksum')
    # yield header
    # while offset + 2 < len(data):
    #     offset, message = next_message(data[offset:])
    #     yield message


def read_path(path):
    with open(path, 'rb') as input:
        return input.read()


def strip_header_crc(data):
    offset, length = unpack('<BxxxI', data[:8])
    size = offset + length + 2
    if len(data) != size:
        raise Exception('Bad length (%d / %d)' % (len(data), size))
    checksum = unpack('<H', data[-2:])[0]
    return data[offset:-2], checksum


def read_header(log, data, messages):
    header = messages.profile_to_message('HEADER')
    return header.raw_to_internal(data, endian=LITTLE)


CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
       0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def check_crc(data, reference):
    checksum = 0
    for byte in data:
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[byte & 0xf]
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[(byte >> 4) & 0xf]
    if checksum != reference:
        raise Exception('Bad checksum (%04x / %04x)' % (checksum, reference))


