
from operator import lt, gt

MIN_CLIMB_DISTANCE_M = 1000
MIN_CLIMB_GRADIENT = 0.03
MAX_CLIMB_REVERSAL = 0.1


def climbs(waypoints):
    '''
    Climbs are found (and defined) by the following process:

    * The largest uphill segment (largest difference in elevation between two points that has a gradient
      within limits) is found.

    * That splits the waypoints into 3 - before climb, climb, after climb.  The start and end sections
      are themselves checked (by starting from above with that segment).

    * For the climb, the largest descent (ie climb going backwards) is found.  If that is more than
      MAX_CLIMB_REVERSAL of the climb (in elevation) then the climb is split into 3.  The start and
      end climbs are themselves checked for reversals; the descent is checked for smaller climbs.

    * Any climbs that survive this process are then trimmed, discarding inital and final sections where
      the gradient is below the cut-off.

    * Finally, surviving climbs that still meet all requirements are "returned".

    This is intended to find the "biggest" climbs that don't include large reversals, and without overlaps.

    (Note that waypoints are in time order)
    '''
    waypoints = [w for w in waypoints if w.elevation is not None]
    if waypoints and (waypoints[-1].distance - waypoints[0].distance) >= MIN_CLIMB_DISTANCE_M:
        up, lo, hi = biggest_climb(waypoints)
        if up:
            a, b, c = split(waypoints, lo, hi)
            yield from climbs(a)
            yield from contiguous(b)
            yield from climbs(c)


def split(waypoints, lo, hi, inside=True):
    i = waypoints.index(lo)
    j = waypoints.index(hi)
    if i > j:
        i, j = j, i
    if inside:
        j += 1
    else:
        i += 1
    return waypoints[:i], waypoints[i:j], waypoints[j:]


def trim(waypoints):
    start, i = 0, len(waypoints)-1
    while i > 0 and waypoints[i].distance < waypoints[0].distance:
        gradient = (waypoints[i].elevation - waypoints[0].elevation) / (waypoints[i].distance - waypoints[0].distance)
        if gradient < MIN_CLIMB_GRADIENT:
            start = i
            break
        i -= 1
    finish, i = len(waypoints)-1, start
    while i < len(waypoints)-1 and waypoints[i].distance < waypoints[-1].distance:
        gradient = (waypoints[-1].elevation - waypoints[i].elevation) / (waypoints[-1].distance - waypoints[i].distance)
        if gradient < MIN_CLIMB_GRADIENT:
            finish = i
        i += 1
    if waypoints[finish].distance - waypoints[start].distance >= MIN_CLIMB_DISTANCE_M:
        # gradient can only have improved, so no need to check again
        yield waypoints[start], waypoints[finish]


def contiguous(waypoints):
    up = waypoints[-1].elevation - waypoints[0].elevation
    along = waypoints[-1].distance - waypoints[0].distance
    if along >= MIN_CLIMB_DISTANCE_M:
        down, lo, hi = biggest_climb(waypoints, reverse=True)
        if down and down > MAX_CLIMB_REVERSAL * up:
            a, b, c = split(waypoints, lo, hi, inside=False)
            yield from contiguous(a)
            yield from climbs(b)
            yield from contiguous(c)
        else:
            yield from trim(waypoints)


def sort(waypoints, reverse=False):
    return sorted(waypoints, key=lambda w: w.elevation, reverse=reverse)


def first_or_none(generator):
    try:
        return next(generator)
    except StopIteration:
        return None


def biggest_climb(waypoints, reverse=False):
    direction = gt if reverse else lt
    best = None, None, None
    if waypoints:
        # this is O(n^2) so try and stuff as much as possible into high-level routines like sort
        highest = sort(waypoints, reverse=True)
        lowest = sort(waypoints)
        for hi in highest:
            # use distance rather than time to avoid division by zero with limited resolution distance
            lo = first_or_none(l for l in lowest if direction(l.distance, hi.distance) and l.elevation < hi.elevation)
            if lo:
                climb = hi.elevation - lo.elevation
                along = hi.distance - lo.distance
                # need to check gradient going forwards because otherwise we could include too much lead-in/out
                if reverse or climb / along >= MIN_CLIMB_GRADIENT:
                    if best[0] is None or climb > best[0]:
                        best = (climb, lo, hi)
            if best[0] and best[0] >= (hi.elevation - lowest[0].elevation):
                break  # abort if there is no way to improve
    return best
