
from json import dumps
from logging import getLogger
from re import sub

from ..squeal import ActivityGroup, Constant, Pipeline, PipelineType, StatisticName, StatisticJournalType, \
    Topic, TopicField, Dummy
from ..squeal.database import connect
from ..squeal.tables.constant import ValidateNamedTuple
from ..squeal.types import long_cls, short_cls
from ..stoats.calculate.activity import ActivityCalculator
from ..stoats.calculate.nearby import Nearby, SimilarityCalculator, NearbyCalculator
from ..stoats.names import DUMMY
from ..uweird.fields.topic import Integer

log = getLogger(__name__)
NEARBY_CNAME = 'Nearby'


def config(*args):
    '''
    Start here to configure the system.  Create an instance on the command line:

        log, db = config('-v', '4')
        print(c...)  todo
        ...
    '''
    ns, db = connect(args)
    return db


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


def add(s, instance):
    '''
    Add an instance to the session (and so to the database), returning the instance.
    You likely don't need this - see the more specific helpers below.

    The instance can of any class that subclasses the Field class from SQLAlchemy.
    In practice, that means most classes in the ch2.squeal.tables mdoule.
    However, only some classes make sense in the context of a configuration, and
    more specific helpers probably already exist for those.
    '''
    s.add(instance)
    return instance


def add_statistics(s, cls, sort, **kargs):
    '''
    Add a class to the statistics pipeline.

    The pipeline classes are invoked when the diary is modified and when activities are added.
    They detect new data and calculate appropriate statistics.
    See the ch2.stoats module for examples.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    return add(s, Pipeline(cls=cls, type=PipelineType.STATISTIC, sort=sort, kargs=kargs))


def add_diary(s, cls, sort, **kargs):
    '''
    Add a class to the diary pipeline.

    The pipeline classes are invoked when the diary is displyed.
    They generate display classes for activity statistics (and similar)
    See the ch2.stoats module for examples.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    return add(s, Pipeline(cls=cls, type=PipelineType.DIARY, sort=sort, kargs=kargs))


def add_monitor(s, cls, sort, **kargs):
    '''
    Add a class to the monitor pipeline.

    The pipeline classes are invoked when activities are imported from FIT files.
    They read the files and create MonitorJournal entries and associated statistics.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    return add(s, Pipeline(cls=cls, type=PipelineType.MONITOR, sort=sort, kargs=kargs))


def add_activity_group(s, name, sort, description=None):
    '''
    Add an activity type to the configuration.

    These are used to group activities (and related statistics).
    So typical entries might be for cycling, running, etc.
    '''
    return add(s, ActivityGroup(name=name, sort=sort, description=description))


def add_activities(s, cls, sort, **kargs):
    '''
    Add a class to the activities pipeline.

    The pipeline classes are invoked when activities are imported from FIT files.
    They read the files and create ActivityJournal entries and associated statistics.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    return add(s, Pipeline(cls=cls, type=PipelineType.ACTIVITY, sort=sort, kargs=kargs))


def add_constant(s, name, description=None, units=None, single=False,
                 statistic_journal_type=StatisticJournalType.INTEGER):
    '''
    Add a constant (not associated with an activity).

    Configuring a constant allows the user to supply a value later, using the `ch2 constant` command.
    This can be useful for values that don't vary often, and so aren't worth adding to the diary.
    An example is FTHR, which you will only measure occasionally, but which is needed when calculating
    activity statistics (also, FTHR can vary by activity, which is why we add a constant per activity).
    '''
    statistic_name = add(s, StatisticName(name=name, owner=Constant, constraint=None,
                                          units=units, description=description,
                                          statistic_journal_type=statistic_journal_type))
    return add(s, Constant(statistic_name=statistic_name, name=name, single=single))


def add_activity_constant(s, activity_group, name, description=None, units=None, single=False,
                          statistic_journal_type=StatisticJournalType.INTEGER):
    '''
    Add a constant associated with an activity.

    Configuring a constant allows the user to supply a value later, using the `ch2 constant` command.
    This can be useful for values that don't vary often, and so aren't worth adding to the diary.
    An example is FTHR, which you will only measure occasionally, but which is needed when calculating
    activity statistics (also, FTHR can vary by activity, which is why we add a constant per activity).
    '''
    if activity_group.id is None:
        s.flush()
    statistic_name = add(s, StatisticName(name=name, owner=Constant, constraint=activity_group,
                                          units=units, description=description,
                                          statistic_journal_type=statistic_journal_type))
    return add(s, Constant(statistic_name=statistic_name, name='%s.%s' % (name, activity_group.name), single=single))


def add_enum_constant(s, name, enum, constraint=None, description=None, units=None, single=False):
    '''
    Add a constant that is a JSON encoded enum.  This is validated before saving.
    '''
    statistic_name = add(s, StatisticName(name=name, owner=Constant, constraint=constraint,
                                          units=units, description=description,
                                          statistic_journal_type=StatisticJournalType.TEXT))
    return add(s, Constant(statistic_name=statistic_name, name=name, single=single,
                           validate_cls=ValidateNamedTuple,
                           validate_args=[], validate_kargs={'tuple_cls': long_cls(enum)}))


def set_constant(s, constant, value, time=None, date=None):
    '''
    Set a constant value.
    '''
    constant.add_value(s, value, time=time, date=date)


def name_constant(short_name, activity_group):
    '''
    Constants typically combine a name with an activity group (because they're specific to a
    particular activity).
    '''
    return '%s.%s' % (sub(r'\s+', '', short_name), sub(r'\s+', '', activity_group.name))


def add_topic(s, name, sort, description=None, schedule=None):
    '''
    Add a root topic.

    Topics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A root topic is usually used as a header to group related children.
    For example, 'DailyDiary' to group diary entries (notes, weight, sleep etc), or 'Plan' to group training plans.
    '''
    return add(s, Topic(name=name, sort=sort, description=description, schedule=schedule))


def add_child_topic(s, parent, name, sort, description=None, schedule=None):
    '''
    Add a child topic.

    Topics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A child topic is used to add additional structrure to an existing topic.
    For example, the parent topic might be "injuries" and permanent, while children are defined for
    specific injuries with a schedule that gives start and end dates.
    '''
    return add(s, Topic(parent=parent, name=name, sort=sort, description=description, schedule=schedule))


def add_topic_field(s, topic, name, sort, type, description=None, units=None, summary=None,
                    display_cls=Integer, **display_kargs):
    '''
    Add a field and associated statistic to a topic entry.

    This is how the user can enter values into the diary.
    The field describes how the values are displayed in the diary.
    The statistic describes how the values are stored in the database.
    '''
    if topic.id is None:
        s.flush()
    statistic_name = add(s, StatisticName(name=name, owner=topic, constraint=topic, statistic_journal_type=type,
                                          description=description, units=units, summary=summary))
    field = add(s, TopicField(topic=topic, sort=sort, type=display_cls.statistic_journal_type,
                              display_cls=display_cls, display_kargs=display_kargs,
                              statistic_name=statistic_name))


def add_nearby(s, sort, activity_group, constraint, latitude, longitude, border=5,
               start='1970', finish='2999', height=10, width=10, fraction=1, constant=NEARBY_CNAME):
    '''
    Add a pipeline task (and related constant) to find nearby activities in a given geographic
    region (specified by latitude, longitude, width and height, all in degrees).
    '''
    activity_group_constraint = str(activity_group)
    nearby_name = name_constant(constant, activity_group)
    nearby = add_enum_constant(s, nearby_name, Nearby, single=True, constraint=activity_group_constraint,
                               description='Data needed to calculate nearby activities - see Nearby enum')
    set_constant(s, nearby, dumps({'constraint': constraint, 'activity_group': activity_group.name,
                                   'border': border, 'start': start, 'finish': finish,
                                   'latitude': latitude, 'longitude': longitude,
                                   'height': height, 'width': width, 'fraction': fraction}))
    add_statistics(s, SimilarityCalculator, sort, nearby=nearby_name,
                   owner_in=short_cls(ActivityCalculator), owner_out=short_cls(SimilarityCalculator))
    add_statistics(s, NearbyCalculator, sort, constraint=constraint,
                   owner_in=short_cls(SimilarityCalculator), owner_out=short_cls(NearbyCalculator))


def add_loader_support(s):
    '''
    Add 'dummy' values used by loader.
    '''
    dummy_source = add(s, Dummy())
    dummy_name = add(s, StatisticName(name=DUMMY, owner=dummy_source,
                                      statistic_journal_type=StatisticJournalType.STATISTIC))
