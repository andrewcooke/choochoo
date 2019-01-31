
from random import uniform
from unittest import TestCase

from ch2.lib.data import MutableAttr
from ch2.stoats.calculate.climb import find_climbs


class TestClimb(TestCase):

    def build_climb(self, xys, speed=10, noise=0, dt=1):
        t0 = 0
        x0, y0 = xys[0]
        t, x, y = t0, x0, y0
        for x1, y1 in xys[1:]:
            t1 = x1 / speed
            while t <= t1:
                x = x0 + (x1 - x0) * (t - t0) / (t1 - t0)
                y = y0 + (y1 - y0) * (t - t0) / (t1 - t0)
                yield MutableAttr({'time': t, 'elevation': y + uniform(-noise, noise), 'distance': x})
                t += dt
            t0, x0, y0 = t1, x1, y1

    def test_build(self):
        waypoints = list(self.build_climb([(0, 0), (1000, 100), (2000, 0)]))
        # print(waypoints)
        self.assertEqual(len(waypoints), 2000 / 10 + 1)
        self.assertEqual(waypoints[0].distance, 0)
        self.assertEqual(waypoints[0].time, 0)
        self.assertEqual(waypoints[0].elevation, 0)
        self.assertEqual(waypoints[-1].distance, 2000)
        self.assertEqual(waypoints[-1].time, 200)
        self.assertEqual(waypoints[-1].elevation, 0)

    def test_single(self):
        waypoints = list(self.build_climb([(0, 0), (1000, 100), (2000, 0)]))
        # print(waypoints)
        c = list(find_climbs(waypoints))
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0][0].time, 0)
        self.assertEqual(c[0][0].distance, 0)
        self.assertEqual(c[0][0].elevation, 0)
        self.assertEqual(c[0][1].time, 100)
        self.assertEqual(c[0][1].distance, 1000)
        self.assertEqual(c[0][1].elevation, 100)

    def test_noisy_single(self):
        for _ in range(10):
            # increase distance to peak to avoid cutoff at 1km
            waypoints = list(self.build_climb([(0, 0), (1100, 100), (2000, 0)], noise=1))
            # print(waypoints)
            c = list(find_climbs(waypoints))
            self.assertEqual(len(c), 1)
            self.assertAlmostEqual(c[0][0].time, 0, delta=5)
            self.assertAlmostEqual(c[0][0].distance, 0, delta=50)
            self.assertAlmostEqual(c[0][0].elevation, 0, delta=5)
            self.assertAlmostEqual(c[0][1].time, 110, delta=5)
            self.assertAlmostEqual(c[0][1].distance, 1100, delta=50)
            self.assertAlmostEqual(c[0][1].elevation, 100, delta=5)

    def test_multiple(self):
        waypoints = list(self.build_climb([(0, 0), (1100, 100), (1200, 90), (1500, 150)]))
        # print(waypoints)
        c = list(find_climbs(waypoints))
        # print(c)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0][1].elevation - c[0][0].elevation, 150)
        waypoints = list(self.build_climb([(0, 0), (1100, 100), (1200, 80), (1500, 150)]))
        # print(waypoints)
        c = list(find_climbs(waypoints))
        # print(c)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0][1].elevation - c[0][0].elevation, 100)
        waypoints = list(self.build_climb([(0, 0), (1100, 100), (1200, 80), (1500, 170)]))
        # print(waypoints)
        c = list(find_climbs(waypoints))
        # print(c)
        self.assertEqual(len(c), 2)
        self.assertEqual(c[0][1].elevation - c[0][0].elevation, 100)
        self.assertEqual(c[1][1].elevation - c[1][0].elevation, 90)


    # def test_noisy_single_to_failure(self):
    #     while True:
    #         waypoints = list(self.build_climb([(0, 0), (1100, 100), (2000, 0)], noise=1))
    #         c = list(climbs(waypoints))
    #         if len(c) != 1:
    #             climbs(waypoints)  # debug breakpoint here



# def analyse_activity(log, s, id):
#     aj = s.query(ActivityJournal).filter(ActivityJournal.id == id).one()
#     waypoints = list(WaypointReader(log, with_timespan=False).read(s, aj, {DISTANCE: 'distance',
#                                                                            ELEVATION: 'elevation'},
#                                                                    SegmentImporter))
#     plots = []
#     for phi in (0.3, 0.4, 0.5, 0.6, 0.7, 1):
#         # this is mainly noise getting things into appropriate forms for plotting...
#         climbs = pd.DataFrame()
#         for lo, hi in find_climbs(waypoints, params=Climb(phi=phi)):
#             climbs = climbs.append(pd.Series({CLIMB_ELEVATION: hi.elevation - lo.elevation,
#                                               CLIMB_DISTANCE: hi.distance - lo.distance}, name=hi.time))
#         all = activity_statistics(s, DISTANCE, ELEVATION, activity_journal_id=id, with_timespan=True).dropna()
#         all[DISTANCE_KM] = all[DISTANCE] / 1000
#         all[ELEVATION_M] = all[ELEVATION]
#         st = [df for id, df in all.groupby('timespan_id')]
#         ys = [df[ELEVATION_M].copy() for df in st]
#         for y, df in zip(ys, st):
#             y.index = df[DISTANCE_KM].copy()
#         f = line_diff_elevation_climbs(400, 200, ys, climbs=climbs, st=st)
#         label = Label(x=220, y=100, x_units='screen', y_units='screen',
#                       text='phi=%.1f (%d)' % (phi, len(climbs)), render_mode='css',
#                       background_fill_color='white', background_fill_alpha=1.0)
#         f.add_layout(label)
#         plots.append(f)
#     SingleShotServer(log, column(row(*plots[:2]), row(*plots[2:4]), row(*plots[4:])),
#                      title='Climb Analysis', template=TEMPLATE, pause=5)
#
#
# def analyse():
#     log, db = config('-v 5')
#     set_log(log)
#     with db.session_context() as s:
#         analyse_activity(log, s, _resolve_activity(s, '2017-09-29 16:30:00', None))
#         analyse_activity(log, s, _resolve_activity(s, '2017-09-01 16:30:00', None))
#         analyse_activity(log, s, _resolve_activity(s, '2017-03-28 16:30:00', None))
#
#
# if __name__ == '__main__':
#     analyse()
