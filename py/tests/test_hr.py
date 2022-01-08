from ch2.data import zone
from tests import LogTestCase


class TestKit(LogTestCase):

    def test_zones(self):
        # zone 1 is 0-50% fthr (upper 50)
        # zone 2 is 50-100% fthr (upper 100)
        # zone 3 is 100-150% fthr (upper 150)
        zones = [0, 50, 100, 150]
        fthr = 100
        self.assertEqual(4, zone(2 * fthr, fthr, zones))
        self.assertEqual(4, zone(1.5 * fthr, fthr, zones))
        self.assertEqual(3.5, zone(1.25 * fthr, fthr, zones))
        self.assertEqual(3, zone(1 * fthr, fthr, zones))
        self.assertEqual(2.5, zone(0.75 * fthr, fthr, zones))
        self.assertEqual(2, zone(0.5 * fthr, fthr, zones))
        self.assertEqual(1.5, zone(0.25 * fthr, fthr, zones))
        self.assertEqual(1, zone(0 * fthr, fthr, zones))
