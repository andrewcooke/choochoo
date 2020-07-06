from hashlib import md5
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


# https://stackoverflow.com/a/3431838
def file_hash(file_path):
    hash = md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    return hash.hexdigest()


def data_hash(data):
    if isinstance(data, str): data = data.encode('utf-8')
    hash = md5()
    hash.update(data)
    return hash.hexdigest()
