from matplotlib.pyplot import figure

ORANGE = '#dd2c00'


def stats(zs):
    lo, hi = min(zs), max(zs)
    return lo, hi - lo


def normalize(xs, ys, preserve_aspect_ratio=True):
    xlo, dx = stats(xs)
    ylo, dy = stats(ys)
    if preserve_aspect_ratio:
        if dx > dy:
            ylo -= (dx - dy) / 2
            dy = dx
        else:
            xlo -= (dy - dx) / 2
            dx = dy
    if dx == 0:
        xlo, dx = xlo - 0.5, 1
    if dy == 0:
        ylo, dy = ylo - 0.5, 1
    return lambda x: (x - xlo) / dx - 0.5, lambda y: (y - ylo) / dy - 0.5, dx, dy


def new_fig(cm=1.5, width=1):
    fig = figure(frameon=False)
    fig.set_size_inches(width * cm / 2.54, cm / 2.54)
    return fig


def new_ax(fig, border=0.2, width=1):
    ax = fig.add_subplot(1, 1, 1)
    for edge in ('top', 'right', 'bottom', 'left'):
        ax.spines[edge].set_visible(False)
    lim = 0.5 * (1 + border)
    ax.set_ylim([-lim, lim])
    lim = 0.5 * (1 + border / width)
    ax.set_xlim([-lim, lim])
    ax.tick_params(labelbottom=False, labelleft=False, length=0)
    ax.set_aspect(aspect=1/width, adjustable='box')
    return ax, lim
