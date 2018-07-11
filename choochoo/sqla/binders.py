

class SqlaStaticBinder:

    def __init__(self, db, log, table, defaults=None):
        if defaults is None: defaults = {}
        self.__db = db
        self.__log = log
        self.__table = table
        self.__defauls = defaults
        self.__instance = None
        self.read()

    def read(self):
        query = self.__db.session.query(self.__table)
        for (k, v) in self.__defaults.items():
            query = query.filter(getattr(self.__table, k) == v)
        self.__instance = query.one_or_none()
        if not self.__instance:
            self.__instance = self.__table(**self.__defaults)
