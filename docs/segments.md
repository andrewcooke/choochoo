
# Segments

If we are going to fit parameters in the [FF-Model](impulse.md) we
need multiple, consistent measurements.  One way of doing this is to
repeatedly ride a selected route at threshold pace.  Over time our
performance should change.

This motivates *segments* in Choochoo.  They automatically detect the
ride and generate the required statistic(s).

## Contents

* [Design](#design)
   * [Data Model](#data-model)
   * [Detection](#detection)
   * [Processing Order](#processing-order)
* [Use](#use)
   * [Definition](#definition)
   * [Statistics](#statistics)
   * [Examples](#examples)

## Design

### Data Model

This work introduces two new entities in the data model: Segments and
SegmentJournals.  These follow the pattern established with Monitors,
Activities, etc:

  * Segment entries define particular segments via start and finish
    points (lat/lon) and distance (m).  They also have names,
    descriptions, and are associated with unique IDs.

  * SegmentJournal identifies *instances* of segments within
    activities.  They associate a Segment and an ActivityJournal and
    provide start and finish times that isolate the segment within the
    activity.

    This is a many-to-many relationship: an activity can contain more
    than one segment (or the same segment, repeated multiple times); a
    segment can be found in more that one activity.

    SegmentJournal is also a Source - it is a source of statistics
    (StatisticJournal entries), and those statistics will be deleted
    when the SegmentJournal entry is deleted.  Since the
    SegmentJournal itself will be deleted when either the associated
    Segment or ActivityJournal is entry is removed this guarantees
    database consistency.

Note that one advantage of this design is that SegmentJournal entries
and any associated statistics can be discarded on database upgrade
(they will be re-created when activities are re-imported).  This
supports easy upgrades while keeping the Segment definitions.

### Detection

The uncertainty and noise in GPS measurements, the sparse and uneven
sampling of GPS points, and the complex topologoy of possible routes
combine to make reliable segment detetcion difficult.

The current algorithm has four parameters, which can be set in the
pipeline configuration (all distances in m):

  * `match_bound` - the size of the region used to make an initial
    detection of activities passing near an endpoint.  Default 25m.

  * `outer_bound` - the maximum distance acceptable for a "single"
    pass near an endpoint.  Default 50m.

  * `inner_bound` - the threshold for the closest distance between
    route and endpoint for the pass to be considered to actually pass
    through the endpoint.  Default 5m.

  * `delta` - the fractional increment when interpolating between GPS
    positions.  Default 0.01 (so ~100 interpolations made between
    positions).

Segment detection is implemented as follows:

  * All points in the activity are checked against an [RTree](rtree)
    containing the known segment start and finish positions to construct
    an initial list of candidates (points in the activity close to a
    segment endpoint).

  * Contiguous candidates for the same start or finish position are
    combined.

  * Start and finish candidates are separated, and grouped by segment.

  * For each segment:

      * Possible pairs of start and finish candidates are considered:
	start candidates are considered in reverse order for the
	activity; finish candidates in normal order (this favours
        shorter times for a single segment).

      * Finish candidates earlier than start candidates are discarded.

      * Finish candidates not within 10% of the segment distance are
        discarded.

      * Start and finish positions are refined:

          * GPS points within the activity to either side of the
            candidate position are included to within `outer_bound`.

          * Starting from the GPS point that implies the shortest
            segment, move away (ie to longer segment distances) in
            `delta` steps, interpolating linearly to subsequent GPS
            points, until at a local miniumum in distance from the
            endpoint (or moving outside `outer_bound`).

          * If this distance is within `inner_bound`, use the
            interpolated time as the refined candidate.

      * If refined start and end positions are found, add the segment
        to the database and remove the candidate points from further
        processing.

This algorithm is clearly an imperfect approximation, but appears to
give reliable results.

### Processing Order

Segments are detected on import in `SegmentImporter` which sub-classes
`ActivityImporter`.  The in-memory waypoints created when the activity
is imported are used for segment detection.  This gives faster
importer and removes complications about dependencies between
activities and segments (separate importers would need to be run
in-order).

## Testing

### Varying `_bound` Parameters

  * `inner_bound` of 2 is too small, but 5 or 10 is fine.

  * A `match_bound` of 5 or 10 seems fine, except for the next point.

  * A `match_bound` 10 combined with an `outer_bound` of 25 matches
    one additional file.

    The "extra" segment comes from 2017-08-10.  Seems that the larger
    `match_bound` found a valid point that then needed a
    correspondingly large `outer_bound` to correctly find the minimum.

    In other words, `match_bound` and `outer_bound` naturally should
    be increased together.  Maybe they can be replaced by a single
    value?

  * A large `match_bound` (going from 10 to 25) messed things up.
    Seems that the `outer_bound` (then < 25) was then too small (see
    above).

  * See matches from a total of 9 files in 2017: 2017-01-18;
    2017-02-09; 2017-05-05; 2017-07-12; 2017-07-14; 2017-08-08;
    2017-08-10; 2017-08-12; 2017-10-04

### varying `delta`

  * Has little effect on running time.

  * Looking at Segment Time, results for `delta` of 0.001 and 0.01 are
    comparable, while 0.1 is sometimes a few seconds different.

## Use

### Definition

Picture of Jupyter here.

### Statistics

Two statistics are current calculated by `StatisticCalculator`:

  * **Segment Time** - The time spent on the segment.  Simply the
    difference between the start and finish times found during segment
    detection.

  * **Segment Heart Rate** - The average heart rate on the segment.
    Weighted by interval to remove any possible bias from GPS
    sampling.  Values at either end of the segment are not treated
    "carefully" (no interpolation past the endpoint; possible loss of
    a value when calculating gaps).

### Examples



