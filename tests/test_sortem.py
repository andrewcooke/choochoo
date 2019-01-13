
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2 import constants
from ch2.command.args import bootstrap_file, V, m, DEV, mm
from ch2.config import default
from ch2.sortem import SRTM1_DIR, ElevationOracle


class TestSortem(TestCase):

    @contextmanager
    def oracle(self):
        with NamedTemporaryFile() as f:
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            args, log, db = bootstrap_file(f, m(V), '5', 'constants', '--set', SRTM1_DIR, '/home/andrew/archive/srtm1')
            constants(args, log, db)
            with db.session_context() as s:
                yield ElevationOracle(log, s)

    def test_read(self):
        with self.oracle() as oracle:
            elevation = oracle.elevation(-33.4489, -70.6693)
            self.assertAlmostEqual(elevation, 544.9599999999932, places=9)

    def test_interpolate(self):
        with self.oracle() as oracle:
            arcsec = 1 / 360
            image = ''
            for i in range(30):
                lat = -33.5 - arcsec * i / 10
                line = ''
                for j in range(60):
                    lon = -70.5 - arcsec * j / 10
                    # factor of 10 here to get visibly nice contours
                    d = int(oracle.elevation(lat, lon) / 10) % 10
                    line += ' .:-=+*#%@'[d]
                image += line
                image += '\n'
        self.assertEqual(image, '''=-:. . @@%%##***++=====---------:::-----:.   @%%##**++====--
*+==--:.@@%%#***+++++==---:::::.......... @@@%%%##**+++=====
#*++=--. @%%##***++*++===-::........    @@%%%%####**++++====
%#*+==-:. %%####*****++===-::.......  @@@%%%%%####**++++====
@%#*+=-..@%%%#%###****+++==--::.....  @@@@%@@%%%%##***++====
 %#*+=:.@@%%%%@%%%%%###***+++=-::....     @@%%%%%##***++++==
 @#*=-. @@@@@        @%%#####*=-:::....   @@%%%%###**+++++==
 %*=-:.  @@ ..::.::..   @@@@%#*=--:...  @@%%%#####**+++++===
 #+=-:.  @ .:---===-::::... @%#+=-:.. @@@%%%%####**++++++===
%*+=-:.  .:==+++**++====---:. %#+=-:. @@%%%%####***++++++==-
#*=-::..:-+**###%%%#****++=-:.@%*+-:.. @%%%####***++++++==--
#+=-:::-=+*#%%%@@@@@%####*++=.@%#*=-:. @@%%##*****+++++====-
*=--:--=+*#%@@  ...  @@@%%#*=-. %#+-:. @@%%##****+++++====--
+=----+*#%@   .:-:::::...@%#*=-:@#*=-. @@@%##****++++====---
+====+*#@ ..:---==-==--::.@%#+-.@#*+-:. @@%%##***+++====----
+++++*#% .:--=+++****+=-:. @#+-:@#*+=::. @%%%##**+++===----:
**##%%@ .:-=+**######*=-:. @#+-.@%*+-::. @%%%##**+++==---:::
%%%@  .::=+*##%%%%@%#*+=-.@%*+-.@%#*=-:. @@@%##***++==---::.
   .::--=+*%%@@@@  @%#+=-.@%#+-. @%#+=:.. @@%##**+++==-:::..
::::-==+**#@@       @@#*=: @#+=:.@%#+=-..  @@%#**++===-::.. 
---=++**#%%  .::::.. @%#+-.@%*=-:@%#+-:::.. @%#**+++=--:..  
***#%%%@@@.:::-----:.@%#+-: %*+=: %*=----:..@%#****+=--:.   
%%%@@  ..:----=====-:.@#*+-.@#*=: %#++==--:. @%#***+=-:..   
  ..:::::-==++***++=-: %#+-.@#*=: @#*++==-:. @%##*++=-:..   
::-===++=++**####*++-: @#+-.@#+=-.@%##*+=-:. @@%#*++=-:..   
++++**##**##%%%%#**+-: %*+-.@#==-:.@%#*+=-.. @%%#*++==-:..  
%%#%%%@%%#%@  @%##*+-: %#+=:@#*+=-: %#*=-::.@%%%#*++==-:....
@@@        ...@%##*+-: %#*=: %#*=-: %#+=-::. @%%#*++==-::...
  ...::::::::.@%#**+-:.@%*+- @%#=:.@%#+=-::.  @%#**+==--::..
.:::--=====--: @%##*=:.@%*+-: @#+-: @#*+=--:. @%#**+==--::..
''')

    def test_edges(self):
        with self.oracle() as oracle:
            delta = 0.00000001
            lat, lon = -34, -71
            for dj in (-1, 0, 1):
                y = lat + dj * delta
                for di in (-1, 0, 1):
                    x = lon + di * delta
                    self.assertAlmostEqual(oracle.elevation(y, x), 645, places=2,
                                           msg='dj %d; di %d' % (dj, di))
