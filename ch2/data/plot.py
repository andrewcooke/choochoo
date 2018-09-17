
import datetime as dt


def boxplot(f, col):
    '''
    Generate a boxplot for a column (andas series) containing a tuple of 5 values
    (index date) as provided by summary statistics,
    '''
    def pick(n):
        def pick(x):
            return x[n] if x else None
        return pick
    q = [col.map(pick(i)) for i in range(5)]
    f.segment(q[0].index, q[0], q[1].index, q[1])
    f.vbar(q[1].index, dt.timedelta(days=20), q[1], q[2], fill_alpha=0)
    f.vbar(q[2].index, dt.timedelta(days=20), q[2], q[3], fill_alpha=0)
    f.segment(q[3].index, q[3], q[4].index, q[4])
