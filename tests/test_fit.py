
from glob import glob
from logging import getLogger, basicConfig, DEBUG
from os.path import basename, join, exists
from sys import stdout
from unittest import TestCase

from ch2.command.args import FIELDS
from ch2.fit.format.read import filtered_records
from ch2.fit.format.records import no_names, append_units, no_bad_values, fix_degrees, chain
from ch2.fit.profile.fields import DynamicField
from ch2.fit.profile.profile import read_external_profile, read_fit
from ch2.fit.summary import summarize, summarize_csv, summarize_tables
from ch2.lib.tests import OutputMixin, HEX_ADDRESS, DROP_HDR_CHK, sub_extn, EXCLUDE, sub_dir


class TestFit(TestCase, OutputMixin):

    def setUp(self):
        basicConfig(stream=stdout, level=DEBUG)
        self.log = getLogger()
        self.test_dir = '/home/andrew/project/ch2/choochoo/data/test'
        self.profile_path = '/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx'

    def test_profile(self):
        nlog, types, messages = read_external_profile(self.log, self.profile_path)
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
            filtered_records(self.log, read_fit(self.log, join(self.test_dir, 'source/personal/2018-07-26-rec.fit')),
                             profile_path=self.profile_path)
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_decode'),
                                  filters=[HEX_ADDRESS]) as output:
            for record in records:
                print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                      file=output)

    def test_dump(self):
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_dump')) as output:
            summarize(self.log, FIELDS, read_fit(self.log, join(self.test_dir, 'source/personal/2018-07-30-rec.fit')),
                      profile_path=self.profile_path, width=80, output=output)

    def test_developer(self):
        with self.assertTextMatch(join(self.test_dir, 'target/sdk/TestFit.test_developer')) as output:
            summarize(self.log, FIELDS, read_fit(self.log, join(self.test_dir, 'source/sdk/DeveloperData.fit')),
                      profile_path=self.profile_path, width=80, output=output)

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
                                      join(self.test_dir, 'source/personal/andrew@acooke.org_24755630065.fit')),
                             profile_path=self.profile_path)
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_timestamp_16'),
                                  filters=[HEX_ADDRESS]) as output:
            for record in records:
                if record.name == 'monitoring':
                    print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                          file=output)

    def standard_csv(self, fit_path, csv_path, filters=None):
        if filters is None: filters = []
        if DROP_HDR_CHK not in filters: filters = [DROP_HDR_CHK] + filters
        with self.assertCSVMatch(csv_path, filters=filters) as output:
            summarize_csv(self.log, read_fit(self.log, fit_path),
                          profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx',
                          warn=True, output=output)

    def standard_csv_dir(self, dir, fit_pattern, exclude=None, filters=None):
        for source_fit_path in glob(join(self.test_dir, 'source', dir, fit_pattern)):
            if not exclude or basename(source_fit_path) not in exclude:
                source_csv_path = sub_extn(source_fit_path, 'csv')
                if exists(source_csv_path):
                    self.standard_csv(source_fit_path, source_csv_path, filters=filters)
                else:
                    self.log.warning('Could not find %s' % source_csv_path)
                target_csv_path = sub_dir(source_csv_path, 'target', 2)
                if exists(target_csv_path):
                    self.standard_csv(source_fit_path, target_csv_path, filters=filters)
                else:
                    self.log.warning('Could not find %s' % target_csv_path)

    def test_sdk_csv(self):
        self.standard_csv_dir('sdk', '*.fit', exclude='Activity.fit')
        # afaict it should be 0, which is mapped by the type.  the value in the CSV makes no sense.
        self.standard_csv_dir('sdk', 'Activity.fit', filters=[EXCLUDE('timer_trigger')])
