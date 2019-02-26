
# Elevation

Many devices don't track elevation.  Choochoo can generate elevation
data by cross-referencing the latitude and longitude from the GPS data
against topographic information from NASA.

  * [SRTM Data](#srtm-data)
  * [Configuration](#configuration)
  * [Smoothing](#smoothing)
  * [Results](#results)

## SRTM Data

The [Shuttle Radar Tomography Mission
(SRTM)](https://www2.jpl.nasa.gov/srtm/) was a project to measure the
"height" almost everywhere on Earth (except for the polar regions)
using radar carried on the Space Shuttle.

These data have been released to the public.  The "best" and most
recent release (in 2014) is called SRTM 3.0 and has a resolution of 1
arcsecond (approximately 30m on the equator).

Using these data is surprisingly easy.  They are packaged into files
covering a square degree, named after the "bottom left" corner.  So
given a position it is easy to know which file to use.  Within the
file the data are packaed as a simple array.

The only problematic part of the process is that downloading the files
requires registration.  I could not automate this (could not get
OAuth2 to work correctly) so you must download the data you need
manually.  The good news is you likely only need one or two files.

## Configuration

Two things need to be done to get elevation working.

First, you must set the directory where the SRTM files will be stored:

    > ch2 constants --set SRTM1.Dir /PATH/TO/SRTM/DIRECTORY

Second, you must download the appropriate data.  You may be able to
find the correct file(s) [here](http://dwtkns.com/srtm30m/) by using
the map.  Otherwise, simply import activity data and read the error
message when Choochoo fails to find the right file.

Once you have the correct files, re-run import to calculate
elevations:

    > ch2 activities --force /PATH/TO/FIT/FILES

## Smoothing

The raw SRTM data appear to be noisy (within Santiago this may be
because of confusion with buildings, but there also appeared to be
noise on rides in open countryside).

I experiemented with smoothing the data on initial interpolation (ie
when generating the elevation for a particular GPS coordinate), but
this (1) appeared to be unstable and (2) did not address "error
amplification" with GPS location errors on steep slopes.

Better results were obtained by extracting the data from the SRTM
arrays using bilinear interpolation (ie no additional smoothing) and
then spline-smoothing *along* the route.  This exploits the fact that
the route ridden is likely to be smoother than the surrounding terrain
(roads and trails naturally follow the smoothest path)

The main disadvantage of this approach is that there is no external,
fixed reference: two crossing routes don't have to share the same
height where they meet.

## Results

![](elevation.png)

![](altitude.png)

The two plots above show the same ride.  GPS altitude is shown in
black; SRTM elevation in red; route-smoothed elevation in blue.

There is a consistent offset between the GPS and SRTM data that I
assume is due to differences in the reference altitude.

To duplicate these results, use the notebook
[here](https://github.com/andrewcooke/choochoo/blob/master/notebooks/elevation/compare-gps.ipynb)
(adjusted for your own data).

