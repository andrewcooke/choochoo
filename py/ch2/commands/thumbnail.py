
from logging import getLogger
from os.path import exists, join

from matplotlib import use
from matplotlib.pyplot import show, figure
from sqlalchemy import func, text

from .args import ACTIVITY, THUMBNAIL_DIR, DISPLAY, CLIMB
from ..data.query import Statistics
from ..names import N
from ..pipeline.read.activity import ActivityReader
from ..sql import ActivityJournal, SectorClimb

log = getLogger(__name__)


def thumbnail(config):
    '''
## thumbnail

    > ch2 thumbnail ACTIVITY-ID
    > ch2 thumbnail DATE

Generate a thumbnail map of the activity route.
    '''
    with config.db.session_context() as s:
        activity_id = parse_activity(s, config.args[ACTIVITY])
        if config.args[DISPLAY]:
            display(s, activity_id, config.args[CLIMB])
        else:
            create_in_cache(config.args._format_path(THUMBNAIL_DIR), s, activity_id, config.args[CLIMB])


def parse_activity(s, text):
    try:
        return int(text)
    except ValueError:
        return ActivityJournal.at(s, text).id


def read_activity(s, activity_id, decimate=10):
    try:
        activity_journal = s.query(ActivityJournal).filter(ActivityJournal.id == activity_id).one()
        df = Statistics(s, activity_journal=activity_journal). \
            by_name(ActivityReader, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y).df
        return df.iloc[::decimate, :]
    except:
        raise Exception(f'{activity_id} is not a valid activity ID')


def read_climb(s, climb_id):
    if climb_id:
        sql = text('''
  with point as (select st_centroid(st_transform(st_setsrid(s.route, sg.srid), 3785)) as point
                   from sector as s,
                        sector_group as sg
                  where s.sector_group_id = sg.id
                    and s.id = :sector_climb_id)
select st_x(point), st_y(point)
  from point; 
''')
        climb = s.connection().execute(sql, sector_climb_id=climb_id).fetchone()
        return climb[0], climb[1]


def stats(zs):
    lo, hi = min(zs), max(zs)
    mid = (lo + hi) / 2
    return lo, mid, hi, hi - lo


def normalize(points):
    xs, ys = zip(*points)
    xlo, xmid, xhi, dx = stats(xs)
    ylo, ymid, yhi, dy = stats(ys)
    if dx > dy:
        ylo -= (dx - dy) / 2
    else:
        xlo -= (dy - dx) / 2
    d = max(dx, dy)
    return [(x - xlo) / d - 0.5 for x in xs], [(y - ylo) / d - 0.5 for y in ys], d


def make_figure(xs, ys, side, grid, cm, border, climb=None):
    fig = figure(frameon=False)
    fig.set_size_inches(cm / 2.54, cm / 2.54)
    ax = fig.add_subplot(1, 1, 1)
    for edge in ('top', 'right', 'bottom', 'left'):
        ax.spines[edge].set_visible(False)
    lim = 0.5 * (1 + border)
    km = 1000 / side
    n = int(lim / (grid * km)) + 1
    ticks = [km * d * grid for d in range(-n, n+1)]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.tick_params(labelbottom=False, labelleft=False, length=0)
    ax.grid(axis='both', color='#535353')
    ax.set_xlim([-lim, lim])
    ax.set_ylim([-lim, lim])
    ax.set_aspect(aspect='equal', adjustable='box')
    ax.plot(xs, ys, color='white')
    ax.plot([xs[0]], [ys[0]], marker='o', color='green', markersize=cm*3)
    ax.plot([xs[-1]], [ys[-1]], marker='o', color='red', markersize=cm*1.5)
    if climb:
        ax.plot([climb[0]], [climb[1]], marker='^', color='white', markersize=cm*3)
        ax.plot([climb[0]], [climb[1]], marker='^', color='black', markersize=cm*1)
    return fig


def fig_from_df(df, grid=10, cm=1.5, border=0.2, climb=None):
    points = [(x, y) for _, (x, y) in df.iterrows()]
    if climb:
        points.append(climb)
    if points:
        xs, ys, side = normalize(points)
    else:
        xs, ys, side = [0, 0], [0, 0], 1
    if climb:
        xs, ys, climb = xs[:-1], ys[:-1], (xs[-1], ys[-1])
    return make_figure(xs, ys, side, grid, cm, border, climb=climb)


def display(s, activity_id, climb_id):
    df = read_activity(s, activity_id)
    use('tkagg')
    fig = fig_from_df(df, climb=read_climb(s, climb_id))
    show()


def create_in_cache(dir, s, activity_id, climb_id):
    path = join(dir, f'{activity_id}.png')
    if not exists(path):
        df = read_activity(s, activity_id)
        use('agg')
        fig = fig_from_df(df, climb=read_climb(s, climb_id))
        fig.savefig(path, transparent=True)
    log.info(f'Thumbnail in {path}')
    return path
