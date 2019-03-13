
from random import uniform
from unittest import TestCase

from ch2.lib.data import MutableAttr
from ch2.data.climb import find_climbs


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

