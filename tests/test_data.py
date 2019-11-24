from json import loads
from logging import getLogger, basicConfig, INFO
from sys import stdout
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2.commands.args import bootstrap_file, m, V
from ch2.lib.data import MutableAttr, reftuple
from ch2.squeal import StatisticJournalFloat, StatisticJournalText, Source
from ch2.squeal.tables.source import SourceType


class TestData(TestCase):

    def setUp(self):
        if not getLogger().handlers:
            basicConfig(stream=stdout, level=INFO)
        self.log = getLogger()

    def test_attr(self):
        d = MutableAttr()
        d['foo'] = 'bar'
        self.assertTrue('foo' in d)
        self.assertEqual(d.foo, 'bar')

    def test_reftuple(self):

        Power = reftuple('Power', 'bike, weight')
        power = Power('${Bike}', '${Weight}')

        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
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
        from ch2.stoats.calculate.power import Power, Bike
        self.assertEqual(Bike.__module__, 'ch2.stoats.calculate.power')
        self.assertEqual(Power.__module__, 'ch2.stoats.calculate.power')
