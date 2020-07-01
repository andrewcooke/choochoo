from os import makedirs
from os.path import dirname, normpath, expanduser
from pathlib import Path


def touch(path, with_dirs=False):
    path = clean_path(path)
    if with_dirs:
        dirs = dirname(path)
        makedirs(dirs, exist_ok=True)
    Path(path).touch()


def clean_path(path):
    # don't use realpath here since it messes up inside docker
    return normpath(expanduser(path))
