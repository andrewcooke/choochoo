from logging import getLogger

log = getLogger(__name__)

__GLOBAL_DEV = False


def set_global_dev(dev):
    global __GLOBAL_DEV
    __GLOBAL_DEV = dev
    log.debug(f'Setting global dev flag: {dev}')


def global_dev():
    global __GLOBAL_DEV
    return __GLOBAL_DEV

