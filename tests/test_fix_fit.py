
from logging import basicConfig, getLogger, INFO
from sys import stdout
from unittest import TestCase

from ch2.fit.fix import fix
from ch2.fit.format.tokens import FileHeader
from ch2.fit.profile.profile import read_fit


class TestFixFit(TestCase):

    def setUp(self):
        basicConfig(stream=stdout, level=INFO)
        self.log = getLogger()

    def test_null(self):
        good = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-08-27-rec.fit')
        same = fix(self.log, bytearray(good))
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_null_drop(self):
        good = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-08-27-rec.fit')
        same = fix(self.log, bytearray(good), drop=True)
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_null_slices(self):
        good = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-08-27-rec.fit')
        same = fix(self.log, bytearray(good), slices=':')
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_drop(self):
        bad = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/other/8CS90646.FIT')
        good = fix(self.log, bad, drop=True)
        self.assertTrue(len(good) < len(bad))

    def test_slices(self):
        bad = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/other/8CS90646.FIT')
        with self.assertRaisesRegexp(Exception, 'unpack requires a buffer of 32 bytes'):
            fix(self.log, bad, slices=':1000')  # first 1k bytes only

    def test_no_last_byte(self):
        good = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-08-27-rec.fit')
        same = fix(self.log, bytearray(good), drop=True)
        self.assertEqual(same, good)
        fixed = fix(self.log, bytearray(good)[:-1], drop=True)
        self.assertEqual(fixed, good)
        fixed = fix(self.log, bytearray(good)[:-2], drop=True)
        self.assertEqual(fixed, good)

    def test_no_header(self):
        good = read_fit(self.log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-08-27-rec.fit')
        same = fix(self.log, bytearray(good), drop=True)
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(same, good)
        header = FileHeader(good)
        with self.assertRaisesRegex(Exception, 'Compressed timestamp with no preceding absolute timestamp'):
            fix(self.log, bytearray(good)[len(header):])
        fixed = fix(self.log, bytearray(good)[len(header):], add_header=True, drop=True)
        self.assertEqual(good, fixed)
        fixed = fix(self.log, bytearray(good), add_header=True, slices=':14,28:')
        self.assertEqual(good, fixed)
