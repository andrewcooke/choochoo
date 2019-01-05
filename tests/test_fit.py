
from _csv import reader
from glob import glob
from itertools import zip_longest
from logging import getLogger, basicConfig, DEBUG
from os.path import splitext, split, join, basename
from re import sub
from sys import stdout
from tempfile import TemporaryDirectory
from unittest import TestCase

from ch2.command.args import FIELDS
from ch2.fit.format.read import filtered_records
from ch2.fit.format.records import no_names, append_units, no_bad_values, fix_degrees, chain
from ch2.fit.profile.fields import DynamicField
from ch2.fit.profile.profile import read_external_profile, read_fit
from ch2.fit.summary import summarize, summarize_csv, summarize_tables
from ch2.lib.tests import OutputMixin, HEX_ADDRESS, DROP_HDR_CHK, sub_extn, EXCLUDE


class TestFit(TestCase, OutputMixin):

    def setUp(self):
        basicConfig(stream=stdout, level=DEBUG)
        self.log = getLogger()

    def test_profile(self):
        nlog, types, messages = read_external_profile(self.log,
                                                      '/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')
        cen = types.profile_to_type('carry_exercise_name')
        self.assertEqual(cen.profile_to_internal('farmers_walk'), 1)
        session = messages.profile_to_message('session')
        field = session.profile_to_field('total_cycles')
        self.assertIsInstance(field, DynamicField)
        for name in field.references:
            self.assertEqual(name, 'sport')
        workout_step = messages.profile_to_message('workout_step')
        field = workout_step.number_to_field(4)
        self.assertEqual(field.name, 'target_value')
        fields = ','.join(sorted(field.references))
        self.assertEqual(fields, 'duration_type,target_type')

    def test_decode(self):
        types, messages, records = \
            filtered_records(self.log,
                             read_fit(self.log,
                                      '/home/andrew/project/ch2/choochoo/data/test/personal/2018-07-26-rec.fit'),
                             profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')
        with self.assertTextMatch(
                '/home/andrew/project/ch2/choochoo/data/test/target/TestFit.test_decode',
                filters=[HEX_ADDRESS]) as output:
            for record in records:
                print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                      file=output)

    def test_dump(self):
        with self.assertTextMatch(
                '/home/andrew/project/ch2/choochoo/data/test/target/TestFit.test_dump') as output:
            path = '/home/andrew/project/ch2/choochoo/data/test/personal/2018-07-30-rec.fit'
            summarize(self.log, FIELDS, read_fit(self.log, path),
                      profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx',
                      width=80, output=output)

    def test_developer(self):
        with self.assertTextMatch(
                '/home/andrew/project/ch2/choochoo/data/test/target/TestFit.test_developer') as output:
            path = '/home/andrew/project/ch2/choochoo/data/test/sdk/DeveloperData.fit'
            summarize(self.log, FIELDS, read_fit(self.log, path),
                      profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx',
                      width=80, output=output)

    def test_csv(self):
        for path in glob('/home/andrew/project/ch2/choochoo/data/test/sdk/*.fit'):
            filters = [DROP_HDR_CHK]
            if path.endswith('Activity.fit'):
                # afaict it should be 0, which is mapped by the type.
                # the value in the CSV makes no sense.
                filters.append(EXCLUDE('timer_trigger'))
            with self.assertCSVMatch(sub_extn(path, 'csv'), filters=filters) as output:
                summarize_csv(self.log, read_fit(self.log, path),
                              profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx',
                              warn=True, output=output)

    def test_personal(self):
        for fit_file in glob('/home/andrew/project/ch2/choochoo/data/test/personal/*.fit'):
            file_name = basename(fit_file)
            with self.assertTextMatch(
                    '/home/andrew/project/ch2/choochoo/data/test/target/TestFit.test_personal:' + file_name) as output:
                summarize_tables(self.log, read_fit(self.log, fit_file), width=80, output=output,
                                 profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')

    def test_timestamp_16(self):
        types, messages, records = \
            filtered_records(self.log,
                             read_fit(self.log,
                                      '/home/andrew/project/ch2/choochoo/data/test/personal/andrew@acooke.org_24755630065.fit'),
                             profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')
        with self.assertTextMatch(
                '/home/andrew/project/ch2/choochoo/data/test/target/TestFit.test_tiemstamp_16',
                filters=[HEX_ADDRESS]) as output:
            for record in records:
                if record.name == 'monitoring':
                    print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                          file=output)
