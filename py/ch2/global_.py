from logging import getLogger

log = getLogger(__name__)

__GLOBAL_DEV = False
__GLOBAL_DATA = None


def set_global_dev(dev):
    global __GLOBAL_DEV
    __GLOBAL_DEV = dev
    log.debug(f'Setting global dev flag: {dev}')


def global_dev():
    global __GLOBAL_DEV
    return __GLOBAL_DEV


def set_global_data(data):
    global __GLOBAL_DATA
    __GLOBAL_DATA = data


def global_data():
    global __GLOBAL_DATA
    return __GLOBAL_DATA
