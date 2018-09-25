
from types import SimpleNamespace

from ..squeal.tables.statistic import StatisticDiary, Statistic


class StatisticMixin:

    def populate_statistics(self, session):
        cls = self.__class__
        cls_name = inspect(cls).tables[0].name
        cls_constraint_attr = cls.__statistic_constraint__
        cls_constraint = getattr(self, cls_constraint_attr)
        time_attr = cls.__statistic_time__
        time = getattr(self, time_attr)
        self.statistics = SimpleNamespace()
        for statistic in session.query(StatisticDiary).join(Statistic). \
                filter(Statistic.cls == cls_name, Statistic.cls_constraint == cls_constraint,
                       StatisticDiary.time == time).all():
            setattr(self.statistics, statistic.statistic.name, statistic)
