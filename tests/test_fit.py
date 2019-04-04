
from glob import glob
from logging import getLogger, basicConfig, INFO
from os.path import basename, join, exists
from sys import stdout
from unittest import TestCase

from ch2.commands.args import FIELDS, TABLES, GREP
from ch2.fit.format.read import filtered_records
from ch2.fit.format.records import no_names, append_units, no_bad_values, fix_degrees, chain, no_units
from ch2.fit.profile.fields import DynamicField
from ch2.fit.profile.profile import read_external_profile, read_fit
from ch2.fit.summary import summarize, summarize_csv, summarize_tables
from ch2.lib.tests import OutputMixin, HEX_ADDRESS, EXC_HDR_CHK, sub_extn, EXC_FLD, sub_dir, RNM_UNKNOWN, ROUND_DISTANCE

log = getLogger(__name__)


class TestFit(TestCase, OutputMixin):

    # some of these tests depend on the width of the window they are run in!  :(
    # (use 80 chars until fixed)

    def setUp(self):
        self.test_dir = 'data/test'
        self.profile_path = 'data/sdk/Profile.xlsx'

    def test_profile(self):
        nlog, types, messages = read_external_profile(log, self.profile_path)
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
            filtered_records(read_fit(log, join(self.test_dir, 'source/personal/2018-07-26-rec.fit')),
                             profile_path=self.profile_path)
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_decode'),
                                  filters=[HEX_ADDRESS]) as output:
            for _, _, record in records:
                print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                      file=output)

    def test_dump(self):
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_dump')) as output:
            summarize(FIELDS, read_fit(log, join(self.test_dir, 'source/personal/2018-07-30-rec.fit')),
                      profile_path=self.profile_path, width=80, output=output)

    def test_developer(self):
        with self.assertTextMatch(join(self.test_dir, 'target/sdk/TestFit.test_developer')) as output:
            summarize(FIELDS, read_fit(log, join(self.test_dir, 'source/sdk/DeveloperData.fit')),
                      profile_path=self.profile_path, width=80, output=output)

    def test_personal(self):
        for fit_file in glob(join(self.test_dir, 'source/personal/*.fit')):
            file_name = basename(fit_file)
            with self.assertTextMatch(
                    join(self.test_dir, 'target/personal/TestFit.test_personal:' + file_name)) as output:
                summarize_tables(read_fit(log, fit_file), width=80, output=output,
                                 profile_path=self.profile_path)

    def test_timestamp_16(self):
        types, messages, records = \
            filtered_records(read_fit(log, join(self.test_dir, 'source/personal/andrew@acooke.org_24755630065.fit')),
                             profile_path=self.profile_path)
        with self.assertTextMatch(join(self.test_dir, 'target/personal/TestFit.test_timestamp_16'),
                                  filters=[HEX_ADDRESS]) as output:
            for _, _, record in records:
                if record.name == 'monitoring':
                    print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)),
                          file=output)

    def standard_csv(self, fit_path, csv_path, filters=None):
        if filters is None: filters = []
        if EXC_HDR_CHK not in filters: filters = [EXC_HDR_CHK] + filters
        with self.assertCSVMatch(csv_path, filters=filters) as output:
            summarize_csv(read_fit(log, fit_path), profile_path=self.profile_path,
                          warn=True, output=output, internal=True)

    def standard_csv_dir(self, dir, fit_pattern, exclude=None, filters=None):
        for source_fit_path in glob(join(self.test_dir, 'source', dir, fit_pattern)):
            if not exclude or basename(source_fit_path) not in exclude:
                source_csv_path = sub_extn(source_fit_path, 'csv')
                if exists(source_csv_path):
                    self.standard_csv(source_fit_path, source_csv_path, filters=filters)
                else:
                    log.warning('Could not find %s' % source_csv_path)
                target_csv_path = sub_dir(source_csv_path, 'target', 2)
                if exists(target_csv_path):
                    self.standard_csv(source_fit_path, target_csv_path, filters=filters)
                else:
                    log.warning('Could not find %s' % target_csv_path)

    def standard_dmp(self, source, target, format, filters=None):
        with self.assertTextMatch(target, filters=filters) as output:
            summarize(format, read_fit(log, source),
                      warn=True, profile_path=self.profile_path, output=output)

    def standard_dmp_dir(self, dir, fit_pattern, format, exclude=None, filters=None):
        for source_fit_path in glob(join(self.test_dir, 'source', dir, fit_pattern)):
            if not exclude or basename(source_fit_path) not in exclude:
                target_dmp_path = sub_extn(sub_dir(source_fit_path, 'target', 2), format[:3])
                self.standard_dmp(source_fit_path, target_dmp_path, format, filters=filters)

    def test_sdk_csv(self):
        self.standard_csv_dir('sdk', '*.fit', exclude='Activity.fit')
        # afaict it should be 0, which is mapped by the type.  the value in the CSV makes no sense.
        self.standard_csv_dir('sdk', 'Activity.fit', filters=[EXC_FLD('timer_trigger')])

    def test_personal_csv(self):
        self.standard_csv_dir('personal', '*.fit', filters=[RNM_UNKNOWN])

    # these are tests only for consistency across releases, not correctness
    def test_personal_tab(self):
        self.standard_dmp_dir('personal', '*.fit', TABLES)

    # these depend on the output from test_fix_fit, so will fail if those change
    def test_pyfitparse_tab(self):
        self.standard_dmp_dir('python-fitparse', '*.fit', TABLES,
                              exclude=['activity-unexpected-eof.fit',  # data size incorrect
                                       'activity-settings-nodata.fit',   # data size incorrect
                                       'activity-filecrc.fit',  # bad checksum
                                       'activity-activity-filecrc.fit',  # data size incorrect
                                       'activity-settings-corruptheader.fit',  # data size incorrect
                                       'event_timestamp.fit',  # data size incorrect
                                       'activity-settings.fit',  # data size incorrect
                                       ])

    # these are tests only for consistency across releases, not correctness
    def test_pyfitparse_fix_tab(self):
        self.standard_dmp_dir('python-fitparse-fix', '*.fit', TABLES)

    def test_pyfitparse_csv(self):
        self.standard_csv_dir('python-fitparse', '*.fit', filters=[RNM_UNKNOWN, ROUND_DISTANCE])

    def test_other_csv(self):
        self.standard_csv_dir('other', '*.fit', filters=[RNM_UNKNOWN, ROUND_DISTANCE])

    def test_grep(self):
        data = read_fit(log, join(self.test_dir, 'source/personal/2018-07-26-rec.fit'))
        summarize(GREP, data, grep=['.*:.*speed>10'])

    def test_python(self):
        # for other-projects.md
        from logging import basicConfig, getLogger, INFO
        from ch2.fit.profile.profile import read_fit, read_profile
        from ch2.fit.format.records import fix_degrees, no_units
        from ch2.fit.format.read import parse_data

        basicConfig(level=INFO)
        log = getLogger()

        data = read_fit(log, 'data/test/source/personal/2018-07-26-rec.fit')
        types, messages = read_profile(log)
        state, tokens = parse_data(data, types, messages)

        LAT, LONG = 'position_lat', 'position_long'
        positions = []

        for offset, token in tokens:
            record = token.parse_token().as_dict(no_units, fix_degrees)
            if record.name == 'record':
                positions.append((record.data[LAT][0], record.data[LONG][0]))

        print('Read %s positions' % len(positions))

        self.assertAlmostEqual(positions[0][0], -33.42, places=1)
        self.assertAlmostEqual(positions[0][1], -70.61, places=1)
