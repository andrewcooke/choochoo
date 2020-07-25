from cProfile import Profile
from contextlib import contextmanager
from glob import glob
from logging import getLogger
from os import makedirs, link, getpid
from os.path import exists, isdir, join, abspath

from ..commands.args import START, DURATION, COMMAND, WORKER, CPROFILE
from ..common.date import now, time_to_local_time
from ..common.io import clean_path

log = getLogger(__name__)


@contextmanager
def profile(args):
    log.debug(args[CPROFILE])
    use_profile = bool(args[CPROFILE])
    dir, profiler, start = 'profile', None, now()
    if use_profile:
        if args[CPROFILE][0]: dir = args[CPROFILE][0]
        profiler, dir = startup(dir)
    try:
        yield
    finally:
        if use_profile:
            worker = args[WORKER] if WORKER in args else ''
            shutdown(profiler, dir, args[COMMAND], start, worker)


def startup(dir):
    dir = abspath(clean_path(dir))
    log.info(f'Will save profile data to {dir} dir')
    if not exists(dir):
        makedirs(dir, exist_ok=True)
    if not isdir(dir):
        raise Exception(f'{dir} is not a path')
    if glob(f'{dir}/*'):
        log.warning(f'{dir} already contains data')
    makedirs(join(dir, START), exist_ok=True)
    makedirs(join(dir, DURATION), exist_ok=True)
    profiler = Profile()
    profiler.enable()
    return profiler, dir


def shutdown(profiler, dir, command, start, worker):
    profiler.disable()
    duration = int(0.5 + (now() - start).total_seconds())
    duration = f'{duration:06d}'
    start = time_to_local_time(start).replace(" ", "T").replace(':', '-')
    pid = str(getpid())
    path_duration = join(dir, DURATION, f'{duration}.{worker}.{command}.{pid}')
    profiler.dump_stats(path_duration)
    log.warning(f'Saving profile data to {path_duration}')
    path_start = join(dir, START, f'{start}.{worker}.{command}.{pid}')
    link(path_duration, path_start)
    log.warning(f'Saving profile data to {path_start}')
