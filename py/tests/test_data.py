from json import loads
from tempfile import TemporaryDirectory
from tests import LogTestCase

from ch2.commands.args import bootstrap_dir, m, V
from ch2.lib.data import MutableAttr, reftuple
from ch2.sql import StatisticJournalFloat, StatisticJournalText, Source
from ch2.sql.tables.source import SourceType


class TestData(LogTestCase):

    def test_attr(self):
        d = MutableAttr()
        d['foo'] = 'bar'
        self.assertTrue('foo' in d)
        self.assertEqual(d.foo, 'bar')

    def test_reftuple(self):

        Power = reftuple('Power', 'bike, weight')
        power = Power('${Bike}', '${Weight}')

        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            with db.session_context() as s:
                source = Source(type=SourceType.SOURCE)
                s.add(source)
                StatisticJournalText.add(s, 'Bike', None, None, self, None, source, '{"mass": 42}', '1980-01-01')
                StatisticJournalFloat.add(s, 'Weight', None, None, self, None, source, 13, '1980-01-01')
            p = power.expand(s, '1990-01-01', default_owner=self)
            p = p._replace(bike=loads(p.bike))
            self.assertEqual(p.weight, 13)
            self.assertEqual(p.bike['mass'], 42)

    def test_types(self):
        from ch2.pipeline.calculate.power import Power, Bike
        self.assertEqual(Bike.__module__, 'ch2.stats.calculate.power')
        self.assertEqual(Power.__module__, 'ch2.stats.calculate.power')
