
from logging import basicConfig, getLogger, INFO, DEBUG
from os.path import join
from sys import stdout
from unittest import TestCase

from ch2.command.args import RECORDS, TABLES
from ch2.fit.fix import fix
from ch2.fit.format.tokens import FileHeader
from ch2.fit.profile.profile import read_fit
from ch2.fit.summary import summarize
from ch2.lib.tests import OutputMixin


class TestFixFit(TestCase, OutputMixin):

    def setUp(self):
        if not getLogger().handlers:
            basicConfig(stream=stdout, level=DEBUG)
        self.log = getLogger()
        self.test_dir = 'data/test'
        self.profile_path = 'data/sdk/Profile.xlsx'

    def test_null(self):
        good = read_fit(self.log, join(self.test_dir, 'source/personal/2018-08-27-rec.fit'))
        same = fix(self.log, bytearray(good))
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_null_drop(self):
        good = read_fit(self.log, join(self.test_dir, 'source/personal/2018-08-27-rec.fit'))
        same = fix(self.log, bytearray(good), drop=True)
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_null_slices(self):
        good = read_fit(self.log, join(self.test_dir, 'source/personal/2018-08-27-rec.fit'))
        same = fix(self.log, bytearray(good), slices=':')
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(good, same)

    def test_drop(self):
        bad = read_fit(self.log, join(self.test_dir, 'source/other/8CS90646.FIT'))
        fixed = fix(self.log, bad, drop=True)
        self.assertTrue(len(fixed) < len(bad))
        with self.assertTextMatch('data/test/target/other/TestFixFit.test_drop') as output:
            summarize(self.log, RECORDS, fixed, output=output)

    def test_slices(self):
        bad = read_fit(self.log, join(self.test_dir, 'source/other/8CS90646.FIT'))
        with self.assertRaisesRegex(Exception, 'Error fixing checksum'):
            fix(self.log, bad, slices=':1000')  # first 1k bytes only

    def test_no_last_byte(self):
        good = read_fit(self.log, join(self.test_dir, 'source/personal/2018-08-27-rec.fit'))
        same = fix(self.log, bytearray(good), drop=True)
        self.assertEqual(same, good)
        fixed = fix(self.log, bytearray(good)[:-1], drop=True)
        self.assertEqual(fixed, good)
        fixed = fix(self.log, bytearray(good)[:-2], drop=True)
        self.assertEqual(fixed, good)

    def test_no_header(self):
        good = read_fit(self.log, join(self.test_dir, 'source/personal/2018-08-27-rec.fit'))
        same = fix(self.log, bytearray(good), drop=True)
        self.assertTrue(good is not same)  # check making a copy
        self.assertEqual(same, good)
        header = FileHeader(good)
        with self.assertRaisesRegex(Exception, 'Error fixing checksum'):
            fix(self.log, bytearray(good)[len(header):])
        fixed = fix(self.log, bytearray(good)[len(header):], add_header=True, drop=True)
        self.assertEqual(good, fixed)
        fixed = fix(self.log, bytearray(good), add_header=True, slices=':14,28:')
        self.assertEqual(good, fixed)

    def test_weird_header(self):
        bad = read_fit(self.log, join(self.test_dir, 'source/other/8CS90646.FIT'))
        old_header = FileHeader(bad)
        fixed = fix(self.log, bytearray(bad), drop=True, header_size=27)
        new_header = FileHeader(fixed)
        self.assertEqual(new_header.header_size, 27)
        self.assertEqual(new_header.protocol_version, old_header.protocol_version)
        self.assertEqual(new_header.profile_version, old_header.profile_version)

    def test_unknown_bad(self):
        bad = read_fit(self.log, join(self.test_dir, 'source/other/2018-04-15-09-18-20.fit'))
        fixed = fix(self.log, bytearray(bad), drop=True)
        with self.assertTextMatch(join(self.test_dir, 'target/other/TestFixFit.test_unknown_bad:1')) as output:
            summarize(self.log, RECORDS, fixed, output=output)
        bad = read_fit(self.log, join(self.test_dir, 'source/other/2018-02-24-10-04-10.fit'))
        fixed = fix(self.log, bytearray(bad), drop=True)
        with self.assertTextMatch(join(self.test_dir, 'target/other/TestFixFit.test_unknown_bad:2')) as output:
            summarize(self.log, RECORDS, fixed, output=output)

    def test_unknown_good(self):
        good = read_fit(self.log, join(self.test_dir, 'source/other/77F73023.FIT'))
        same = fix(self.log, bytearray(good))
        self.assertEqual(good, same)
        self.assertFalse(good is same)

    # TODO - DOES NOT NEED FIX
    # def test_scaled(self):
    #     bad = read_fit(self.log, join(self.test_dir, 'source/other/2018-05-30-22-00-44.fit'))
    #     fixed = fix(self.log, bytearray(bad), drop=True, max_drop_cnt=2)
    #     with self.assertTextMatch(join(self.test_dir, 'target/other/TestFixFit.test_scaled')) as output:
    #         summarize(self.log, TABLES, fixed, output=output)

    def test_pyfitparse_fix_header(self):
        for file in ('activity-unexpected-eof.fit',  # data size incorrect
                     'activity-settings-nodata.fit',   # data size incorrect
                     # 'activity-filecrc.fit',  # bad checksum  TODO - DOES NOT NEED DROP
                     # 'activity-activity-filecrc.fit',  # data size incorrect  TODO - DOES NOT NEED DROP
                     'activity-settings-corruptheader.fit',  # data size incorrect
                     # 'activity-settings.fit',  # data size incorrect  TODO - DOES NOT NEED DROP
                     ):
            bad = read_fit(self.log, join(self.test_dir, 'source/python-fitparse', file))
            with self.assertBinaryMatch(join(self.test_dir, 'source/python-fitparse-fix', file)) as output:
                output.write(fix(self.log, bad, drop=True))

    def test_pyfitparse_fix_header_2(self):
        for file in (#'event_timestamp.fit',  # data size incorrect
                     #'antfs-dump.63.fit',  # strange timestamp
                     #'compressed-speed-distance.fit',  # strange timestamp
                     ):
            bad = read_fit(self.log, join(self.test_dir, 'source/python-fitparse', file))
            with self.assertBinaryMatch(join(self.test_dir, 'source/python-fitparse-fix', file)) as output:
                output.write(fix(self.log, bad, drop=True, max_drop_cnt=2))

