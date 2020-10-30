
from logging import getLogger
from os.path import join, exists

from matplotlib import use
from matplotlib.pyplot import show, figure
from sqlalchemy import alias

from .args import ACTIVITY, IMAGE_DIR, DISPLAY, STATISTIC, SPARKLINE, SECTOR, INVERT
from ..common.log import log_current_exception
from ..common.plot import new_fig, new_ax, normalize, ORANGE
from ..sql import StatisticJournal, Sector, ActivityJournal
from ..sql.tables.sector import SectorJournal

log = getLogger(__name__)


def sparkline(config):
    '''
## sparkline

    > ch2 sparkline SECTOR-ID

Generate a sparkline plot of the statistic.
    '''
    with config.db.session_context() as s:
        if config.args[DISPLAY]:
            display(s, config.args[STATISTIC], config.args[SECTOR], config.args[ACTIVITY], config.args[INVERT])
        else:
            create_in_cache(config.args._format_path(IMAGE_DIR), s,
                            config.args[STATISTIC], config.args[SECTOR], config.args[ACTIVITY], config.args[INVERT])


def read_statistic(s, statistic_id, sector_id, activity_id):
    try:
        if sector_id:
            instances = s.query(StatisticJournal, ActivityJournal). \
                join(SectorJournal, SectorJournal.id == StatisticJournal.source_id). \
                join(Sector, Sector.id == SectorJournal.sector_id). \
                join(ActivityJournal, ActivityJournal.id == SectorJournal.activity_journal_id). \
                filter(Sector.id == sector_id,
                       StatisticJournal.statistic_name_id == statistic_id). \
                order_by(StatisticJournal.time).all()
        else:
            instances = s.query(StatisticJournal, ActivityJournal). \
                filter(ActivityJournal.id == StatisticJournal.source_id). \
                filter(StatisticJournal.statistic_name_id == statistic_id). \
                order_by(StatisticJournal.time).all()
        if activity_id:
            activity_journal = ActivityJournal.from_id(s, activity_id)
            data = [(instance[0].time, instance[0].value, instance[1].id == activity_id)
                    for instance in instances if instance[1].activity_group_id == activity_journal.activity_group_id]
        else:
            data = [(instance[0].time, instance[0].value, False) for instance in instances]
        if data:
            # we have no x units - just need a int/float value to scale
            t0 = data[0][0]
            data = [((datum[0] - t0).total_seconds(), datum[1], datum[2]) for datum in data]
            return list(zip(*data))
        else:
            return [], [], []
    except:
        log_current_exception()
        raise Exception(f'{statistic_id} is not a valid statistic name ID')


def fig_from_data(data, cm=1, width=7, invert=False):
    fig = new_fig(cm=cm, width=width)
    ax, _ = new_ax(fig, width=width)
    xs, ys, _ = data
    if xs:
        if invert: ys = [1/y for y in ys]
        fx, fy, _, _ = normalize(xs, ys, preserve_aspect_ratio=False)
        xs, ys = [fx(x) for x in xs], [fy(y) for y in ys]
        ax.plot(xs, ys, color='grey')
        ax.plot(xs, ys, marker='o', color='white', linewidth=0, markersize=cm)
        for (x, y, activity) in zip(*data):
            if invert: y = 1 / y
            if activity: ax.plot([fx(x)], [fy(y)], marker='o', color=ORANGE, markersize=cm*2)
    return fig


def display(s, statistic_id, sector_id, activity_id, invert=False):
    data = read_statistic(s, statistic_id, sector_id, activity_id)
    use('tkagg')
    fig = fig_from_data(data, invert=invert)
    fig.gca().set_facecolor('black')
    show()


def create_in_cache(dir, s, statistic_id, sector_id, activity_id, invert=False):
    path = join(dir, f'{SPARKLINE}-{statistic_id}:{sector_id}:{activity_id}:{invert}.png')
    if not exists(path):
        data = read_statistic(s, statistic_id, sector_id, activity_id)
        use('agg')
        fig = fig_from_data(data, invert=invert)
        fig.savefig(path, transparent=True)
    log.info(f'Sparkline in {path}')
    return path
