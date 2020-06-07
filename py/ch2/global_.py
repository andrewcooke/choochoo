from logging import getLogger

log = getLogger(__name__)

__GLOBAL_DEV = False
__GLOBAL_SYS = None


def set_global_dev(dev):
    global __GLOBAL_DEV
    __GLOBAL_DEV = dev
    log.debug(f'Setting global dev flag: {dev}')


def global_dev():
    global __GLOBAL_DEV
    return __GLOBAL_DEV


def set_global_sys(sys):
    global __GLOBAL_SYS
    __GLOBAL_SYS = sys


def global_sys():
    global __GLOBAL_SYS
    return __GLOBAL_SYS

