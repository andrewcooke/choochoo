
from collections import namedtuple

# a climb of 80m is roughly equivalent to a score of 8000 on strava's weird approach -
# https://support.strava.com/hc/en-us/articles/216917057-How-are-Strava-climbs-categorized-For-Rides-
MIN_CLIMB_ELEVATION = 80
MIN_CLIMB_GRADIENT = 3
MAX_CLIMB_REVERSAL = 0.1

# trade-off between pure elevation (0) and pure gradient (1)
CLIMB_PHI = 0.6


Climb = namedtuple('Climb', 'phi, min_elevation, min_gradient, max_reversal',
                   defaults=(CLIMB_PHI, MIN_CLIMB_ELEVATION, MIN_CLIMB_GRADIENT, MAX_CLIMB_REVERSAL))


def find_climbs(waypoints, params=Climb()):
    waypoints = [w for w in waypoints if w.elevation is not None]
    if waypoints:
        mn, mx = min(w.elevation for w in waypoints), max(w.elevation for w in waypoints)
        if mx - mn > params.min_elevation:
            score, lo, hi = biggest_climb(waypoints, params=params)
            if score:
                a, b, c = split(waypoints, lo, hi)
                yield from find_climbs(a, params=params)
                yield from contiguous(b, params=params)
                yield from find_climbs(c, params=params)


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


def contiguous(waypoints, params=Climb()):
    up = waypoints[-1].elevation - waypoints[0].elevation
    if up >= params.min_elevation:
        down, lo, hi = biggest_reversal(waypoints)
        if down and down > params.max_reversal * up:
            a, b, c = split(waypoints, lo, hi, inside=False)
            yield from contiguous(a, params=params)
            yield from find_climbs(b, params=params)
            yield from contiguous(c, params=params)
        else:
            yield waypoints[0], waypoints[-1]


def sort(waypoints, reverse=False):
    return sorted(waypoints, key=lambda w: w.elevation, reverse=reverse)


def first_or_none(generator):
    try:
        return next(generator)
    except StopIteration:
        return None


def biggest_reversal(waypoints):
    best = None, None, None
    if waypoints:
        highest = sort(waypoints, reverse=True)
        lowest = sort(waypoints)
        for hi in highest:
            lo = first_or_none(l for l in lowest if l.distance > hi.distance and l.elevation < hi.elevation)
            if lo:
                drop = hi.elevation - lo.elevation
                # if not reverse: print(score, hi.elevation, lo.elevation)
                if best[0] is None or drop > best[0]:
                    best = (drop, lo, hi)
            if best[0] and best[0] > hi.elevation - lowest[0].elevation:
                break  # exit if there is no way to improve
    return best


def biggest_climb(waypoints, params=Climb(), grid=10):
    if len(waypoints) > 100 * grid:
        found, lo, hi = search(waypoints[::grid], params=params)
        if found:
            i, j = waypoints.index(lo), waypoints.index(hi)
            if i + grid >= j - grid:
                waypoints = waypoints[max(i-grid, 0):j+grid]
            else:
                waypoints = waypoints[max(i-grid, 0):i+grid] + waypoints[max(j-grid, 0):j+grid]
        else:
            return None, None, None
    return search(waypoints, params=params)


def search(waypoints, params=Climb()):
    best = None, None, None
    if waypoints:
        highest = sort(waypoints, reverse=True)
        lowest = sort(waypoints)
        for hi in highest:
            # use distance rather than time to avoid division by zero with limited resolution distance
            for lo in filter(lambda lo: lo.distance < hi.distance and
                                        hi.elevation - lo.elevation > params.min_elevation and
                                        100 * (hi.elevation - lo.elevation) / (hi.distance - lo.distance) >
                                        params.min_gradient,
                             lowest):
                score = (hi.elevation - lo.elevation) / (hi.distance - lo.distance) ** params.phi
                if best[0] is None or score > best[0]:
                    best = (score, lo, hi)
            if (hi.elevation - lowest[0].elevation) < params.min_elevation:
                break  # abort if there is no valid future value
    return best
