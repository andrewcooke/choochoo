
from ....squeal.tables.system import SystemWorker


class Workers:

    def __init__(self, log, s, n_parallel, owner, constraint=None):
        self.log = log
        self.s = s
        self.n_parallel = n_parallel
        self.owner = owner
        self.constraint = constraint

    def clear(self):
        for worker in self.s.query(SystemWorker). \
                filter(SystemWorker.owner == self.owner,
                       SystemWorker.constraint == self.constraint).all():
            

