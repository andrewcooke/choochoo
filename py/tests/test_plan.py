from ch2.commands.args import V, DEV, bootstrap_db
from ch2.common.args import mm, m
from ch2.common.date import to_date, add_date
from ch2.config.plan.british import twelve_week_improver
from ch2.config.plan.exponential import exponential_time, exponential_distance
from ch2.config.profiles.default import default
from ch2.sql.tables.topic import DiaryTopic
from tests import LogTestCase, random_test_user


class TestPlan(LogTestCase):

    def test_british(self):
        user = random_test_user()
        config = bootstrap_db(user, m(V), '5', mm(DEV), configurator=default)
        plan = twelve_week_improver('2018-07-25')
        plan.create(config.db)
        with config.db.session_context() as s:
            root = s.query(DiaryTopic).filter(DiaryTopic.parent_id == None, DiaryTopic.title == 'Plan').one()
            self.assertEqual(len(root.children), 1)
            self.assertTrue(root.schedule)
            self.assertEqual(root.schedule.start, to_date('2018-07-25'))
            self.assertEqual(root.schedule.finish, add_date('2018-07-25', (12, 'w')))
            parent = root.children[0]
            self.assertEqual(len(parent.children), 7)
            for child in parent.children:
                print(child)

    def test_exponential_time(self):
        user = random_test_user()
        config = bootstrap_db(user, m(V), '5', mm(DEV), configurator=default)
        plan = exponential_time('Time test', '2d[2]', '20M', 5, '2018-07-25', '3m')
        plan.create(config.db)
        with config.db.session_context() as s:
            root = s.query(DiaryTopic).filter(DiaryTopic.parent_id == None, DiaryTopic.title == 'Plan').one()
            self.assertEqual(len(root.children), 1)
            parent = root.children[0]
            self.assertEqual(len(parent.children), 46)
            for child in parent.children:
                print(child)

    def test_exponential_distance(self):
        user = random_test_user()
        config = bootstrap_db(user, m(V), '5', mm(DEV), configurator=default)
        plan = exponential_distance('Distance test', 'w[mon,wed,fri]', '20km', 5, '2018-07-25', '1m')
        plan.create(config.db)
        with config.db.session_context() as s:
            root = s.query(DiaryTopic).filter(DiaryTopic.parent_id == None, DiaryTopic.title == 'Plan').one()
            self.assertEqual(len(root.children), 1)
            parent = root.children[0]
            self.assertEqual(len(parent.children), 14)
            for child in parent.children:
                print(child)
