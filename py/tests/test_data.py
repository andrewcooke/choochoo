from json import loads
from tempfile import TemporaryDirectory

from ch2.commands.args import bootstrap_dir, m, V
from ch2.lib.data import MutableAttr, reftuple
from ch2.sql import StatisticJournalFloat, StatisticJournalText, Source
from ch2.sql.tables.source import SourceType
from tests import LogTestCase


class TestData(LogTestCase):

    def test_attr(self):
        d = MutableAttr()
        d['foo'] = 'bar'
        self.assertTrue('foo' in d)
        self.assertEqual(d.foo, 'bar')

    def test_reftuple(self):

        Power = reftuple('Power', 'bike, weight')
        power = Power('${bike}', '${weight}')

        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            with db.session_context() as s:
                source = Source(type=SourceType.SOURCE)
                s.add(source)
                StatisticJournalText.add(s, 'Bike', None, None, self, source, '{"mass": 42}', '1980-01-01')
                StatisticJournalFloat.add(s, 'Weight', None, None, self, source, 13, '1980-01-01')
            p = power.expand(s, '1990-01-01', default_owner=self)
            p = p._replace(bike=loads(p.bike))
            self.assertEqual(p.weight, 13)
            self.assertEqual(p.bike['mass'], 42)

    def test_types(self):
        from ch2.pipeline.calculate.power import PowerModel, BikeModel
        self.assertEqual(BikeModel.__module__, 'ch2.pipeline.calculate.power')
        self.assertEqual(PowerModel.__module__, 'ch2.pipeline.calculate.power')
