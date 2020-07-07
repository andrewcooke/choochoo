from logging import getLogger

from sqlalchemy.sql.functions import count

from ch2.commands.args import V, DEV, FORCE, bootstrap_db
from ch2.commands.constants import constants
from ch2.common.args import mm, m
from ch2.config.profile.default import default
from ch2.sql.tables.constant import Constant
from tests import LogTestCase, random_test_user

log = getLogger(__name__)


class TestConstant(LogTestCase):

    def test_constant(self):
        user = random_test_user()
        config = bootstrap_db(user, m(V), '5')
        bootstrap_db(user, m(V), '5', mm(DEV), configurator=default)
        with config.db.session_context() as s:
            n = s.query(count(Constant.id)).scalar()
            self.assertEqual(n, 14)
        config = bootstrap_db(user, m(V), '5', 'constants', 'set', 'fthr:%', '154', mm(FORCE))
        constants(config)
        with config.db.session_context() as s:
            n = s.query(count(Constant.id)).scalar()
            self.assertEqual(n, 14)
            # todo - maybe test for value?
            # todo - now that this is defined anyway, change the test?
