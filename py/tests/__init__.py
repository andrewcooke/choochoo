import datetime as dt
from logging import getLogger
from unittest import TestCase

from ch2 import PROGNAME
from ch2.common.args import mm
from ch2.common.io import data_hash
from ch2.common.log import configure_log
from ch2.commands.args import make_parser, NamespaceWithVariables
from ch2.common.names import USER
from ch2.common.user import make_user_database
from ch2.sql.system import Data

log = getLogger(__name__)


class LogTestCase(TestCase):

    def setUp(self):
        configure_log(PROGNAME, '/tmp/ch2-test.log', verbosity=5)


def random_test_user(args=(mm(USER), 'postgres')):
    parser = make_parser()
    ns = NamespaceWithVariables(parser.parse_args(args=args), PROGNAME)
    data = Data(ns)
    user = data_hash(str(dt.datetime.now()))[:6]
    log.info(f'USer/database {user}')
    db = make_user_database(data, user, '')
    return user
