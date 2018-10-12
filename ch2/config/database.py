from ch2.uweird.fields import Integer
from ..command.args import parser, NamespaceWithVariables, NO_OP
from ..lib.log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity
from ..squeal.tables.constant import Constant
from ..squeal.tables.statistic import StatisticPipeline, Statistic, StatisticType
from ..squeal.tables.topic import Topic, TopicField


def config(*args):
    '''
    Start here to configure the system.  Create an instance on the command line:

        log, db = config('-v', '4')
        print(c...)  todo
        ...
    '''
    p = parser()
    args = list(args)
    args.append(NO_OP)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return log, db


class Counter:

    def __init__(self, start=10, delta=10):
        self.__start = start
        self.__delta = delta
        self.__previous = None

    def __call__(self, reset=None, delta=None):
        if delta is not None:
            if delta < 1:
                raise Exception('Negative increment')
            self.__delta = delta
        if reset is None:
            if self.__previous is None:
                self.__previous = self.__start
            else:
                self.__previous += self.__delta
        else:
            if reset <= self.__previous:
                raise Exception('Sort not increasing with reset')
            else:
                self.__previous = reset
        return self.__previous


def add(session, instance):
    session.add(instance)
    return instance


def add_pipeline(session, cls, sort, **kargs):
    return add(session, StatisticPipeline(cls=cls, sort=sort, kargs=kargs))


def add_activity(session, name, sort, description=None):
    return add(session, Activity(name=name, sort=sort, description=description))


def add_activity_constant(session, activity, name, description=None, units=None, type=StatisticType.INTEGER):
    statistic = add(session, Statistic(name=name, owner=Constant, constraint=activity.id, units=units,
                                       description=description))
    constant = add(session, Constant(type=type, name='%s.%s' % (name, activity.name), statistic=statistic))


def add_topic(session, name, sort, description=None, schedule=None):
    return add(session, Topic(name=name, sort=sort, description=description, schedule=schedule))


def add_child_topic(session, parent, name, sort, description=None, schedule=None):
    return add(session, Topic(parent=parent, name=name, sort=sort, description=description, schedule=schedule))


def add_topic_field(session, topic, name, sort, description=None, units=None, summary=None,
                    display_cls=Integer, **display_kargs):
    statistic = add(session, Statistic(name=name, owner=topic, constraint=topic.id,
                                       description=description, units=units, summary=summary))
    field = add(session, TopicField(topic=topic, sort=sort, type=display_cls.statistic_type,
                                    display_cls=display_cls, display_kargs=display_kargs,
                                    statistic=statistic))
