
from logging import getLogger
from os.path import join, exists

from matplotlib import use
from matplotlib.pyplot import show, figure

from .args import ACTIVITY, IMAGE_DIR, DISPLAY, STATISTIC, SPARKLINE, SECTOR
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
            display(s, config.args[STATISTIC], config.args[SECTOR], config.args[ACTIVITY])
        else:
            create_in_cache(config.args._format_path(IMAGE_DIR), s,
                            config.args[STATISTIC], config.args[SECTOR], config.args[ACTIVITY])


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
                join(ActivityJournal.id == StatisticJournal.source_id). \
                filter(StatisticJournal.statistic_name_id == statistic_id). \
                order_by(StatisticJournal.time).all()
        data = [(instance[0].time, instance[0].value, instance[1].id == activity_id) for instance in instances]
        if data:
            # we have no x units - just need a int/float value to scale
            t0 = data[0][0]
            data = [((datum[0] - t0).total_seconds(), datum[1], datum[2]) for datum in data]
            return zip(*data)
        else:
            return [], [], []
    except:
        log_current_exception()
        raise Exception(f'{statistic_id} is not a valid statistic name ID')


def fig_from_data(data, cm=1.5, width=2):
    fig = new_fig(cm=cm, width=width)
    ax, _ = new_ax(fig, width=width)
    xs, ys, _ = data
    if xs:
        fx, fy, _, _ = normalize(xs, ys, preserve_aspect_ratio=False)
        xs, ys = [fx(x) for x in xs], [fy(y) for y in ys]
        ax.plot(xs, ys, color='white')
        for (x, y, activity) in zip(*data):
            if activity:
                ax.plot([fx(x)], [fy(y)], marker='o', color=ORANGE, markersize=cm*2)
    return fig


def display(s, statistic_id, sector_id, activity_id):
    data = read_statistic(s, statistic_id, sector_id, activity_id)
    use('tkagg')
    fig = fig_from_data(data)
    fig.gca().set_facecolor('black')
    show()


def create_in_cache(dir, s, statistic_id, sector_id, activity_id):
    path = join(dir, f'{SPARKLINE}-{statistic_id}:{sector_id}:{activity_id}.png')
    if not exists(path):
        data = read_statistic(s, statistic_id, sector_id, activity_id)
        use('agg')
        fig = fig_from_data(data)
        fig.savefig(path, transparent=True)
    log.info(f'Sparkline in {path}')
    return path
