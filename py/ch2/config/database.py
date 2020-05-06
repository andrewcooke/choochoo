from json import dumps
from logging import getLogger
from re import sub

from ..names import DUMMY, ALL
from ..pipeline.calculate.activity import ActivityCalculator
from ..pipeline.calculate.nearby import Nearby, SimilarityCalculator, NearbyCalculator
from ..sql import ActivityGroup, Constant, Pipeline, PipelineType, StatisticName, StatisticJournalType, \
    DiaryTopic, DiaryTopicField, Dummy, ActivityTopic, ActivityTopicField
from ..sql.tables.constant import ValidateNamedTuple
from ..sql.types import long_cls, short_cls

log = getLogger(__name__)
NEARBY_CNAME = 'Nearby'


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
    In practice, that means most classes in the ch2.sql.tables module.
    However, only some classes make sense in the context of a configuration, and
    more specific helpers probably already exist for those.
    '''
    s.add(instance)
    return instance


def add_activity_group(s, name, sort, description=None):
    '''
    Add an activity type to the configuration.

    These are used to group activities (and related statistics).
    So typical entries might be for cycling, running, etc.
    '''
    return add(s, ActivityGroup(name=name, sort=sort, description=description))


def add_statistics(s, cls, sort, **kargs):
    '''
    Add a class to the statistics pipeline.

    The pipeline classes are invoked when the diary is modified and when activities are added.
    They detect new data and calculate appropriate statistics.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    log.debug(f'Adding statistic pipeline {cls}')
    return add(s, Pipeline(cls=cls, type=PipelineType.CALCULATE, sort=sort, kargs=kargs))


def add_displayer(s, cls, sort, **kargs):
    '''
    Add a class to the diary pipeline.

    The pipeline classes are invoked when the diary is displayed.
    They generate display classes for activity statistics (and similar)

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    log.debug(f'Adding displayer pipeline {cls}')
    return add(s, Pipeline(cls=cls, type=PipelineType.DISPLAY, sort=sort, kargs=kargs))


def add_activity_displayer_delegate(s, cls, sort, **kargs):
    '''
    Add a class to the activity displayer pipeline.

    The pipeline classes are invoked when the diary is displayed, for each activity.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    log.debug(f'Adding activity displayer pipeline {cls}')
    return add(s, Pipeline(cls=cls, type=PipelineType.DISPLAY_ACTIVITY, sort=sort, kargs=kargs))


def add_monitor(s, cls, sort, **kargs):
    '''
    Add a class to the monitor pipeline.

    The pipeline classes are invoked when activities are imported from FIT files.
    They read the files and create MonitorJournal entries and associated statistics.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    log.debug(f'Adding monitor pipeline {cls}')
    return add(s, Pipeline(cls=cls, type=PipelineType.READ_MONITOR, sort=sort, kargs=kargs))


def add_activities(s, cls, sort, **kargs):
    '''
    Add a class to the activities pipeline.

    The pipeline classes are invoked when activities are imported from FIT files.
    They read the files and create ActivityJournal entries and associated statistics.

    The sort argument fixes the order in which the classes are instantiated and called and can
    be an integer or a callable (that returns an integer) like Counter above.

    The kargs are passed to the constructor and so can be used to customize the processing.
    '''
    log.debug(f'Loading activity pipeline {cls}')
    return add(s, Pipeline(cls=cls, type=PipelineType.READ_ACTIVITY, sort=sort, kargs=kargs))


def add_constant(s, name, value, description=None, units=None, single=False,
                 statistic_journal_type=StatisticJournalType.INTEGER, activity_group=ALL,
                 time=0.0):
    '''
    Add a constant (not associated with an activity).

    Configuring a constant allows the user to supply a value later, using the `ch2 constant` command.
    This can be useful for values that don't vary often, and so aren't worth adding to the diary.
    An example is FTHR, which you will only measure occasionally, but which is needed when calculating
    activity statistics (also, FTHR can vary by activity, which is why we add a constant per activity).
    '''
    log.debug(f'Adding constant {name}')
    statistic_name = add(s, StatisticName(name=name, owner=Constant,
                                          activity_group=ActivityGroup.from_name(s, activity_group),
                                          units=units, description=description,
                                          statistic_journal_type=statistic_journal_type))
    constant = add(s, Constant(statistic_name=statistic_name, name=name, single=single))
    if value:
        constant.add_value(s, value, time=time)
    else:
        log.warning(f'No value for constant {name}')
    return constant


def add_activity_constant(s, activity_group, name, value, description=None, units=None, single=False,
                          statistic_journal_type=StatisticJournalType.INTEGER, time=0.0):
    '''
    Add a constant associated with an activity.

    Configuring a constant allows the user to modify a value later, using the `ch2 constant` command.
    This can be useful for values that don't vary often, and so aren't worth adding to the diary.
    An example is FTHR, which you will only measure occasionally, but which is needed when calculating
    activity statistics (also, FTHR can vary by activity, which is why we add a constant per activity).
    '''
    if activity_group.id is None:
        s.flush()
    statistic_name = add(s, StatisticName(name=name, owner=Constant, activity_group=activity_group,
                                          units=units, description=description,
                                          statistic_journal_type=statistic_journal_type))
    log.debug(f'Adding activity constant {name}')
    constant = add(s, Constant(statistic_name=statistic_name, name='%s.%s' % (name, activity_group.name),
                               single=single))
    if value:
        constant.add_value(s, value, time=time)
    else:
        log.warning(f'No value for constant {name}')
    return constant


def add_enum_constant(s, name, enum, value,
                      activity_group=ALL, description=None, units=None, single=False, time=0.0):
    '''
    Add a constant that is a JSON encoded enum.  This is validated before saving.
    '''
    statistic_name = add(s, StatisticName(name=name, owner=Constant,
                                          activity_group=ActivityGroup.from_name(s, activity_group),
                                          units=units, description=description,
                                          statistic_journal_type=StatisticJournalType.TEXT))
    constant_name = name_constant(s, name, activity_group)
    constant = add(s, Constant(statistic_name=statistic_name, name=constant_name, single=single,
                               validate_cls=ValidateNamedTuple,
                               validate_args=[], validate_kargs={'tuple_cls': long_cls(enum)}))
    if value:
        constant.add_value(s, dumps(value), time=time)
    else:
        log.warning(f'No value for constant {name}')
    return constant


def set_constant(s, constant, value, time=None, date=None):
    '''
    Set a constant value.
    '''
    constant.add_value(s, value, time=time, date=date)


def name_constant(s, short_name, activity_group=ALL):
    '''
    Constants typically combine a name with an activity group (because they're specific to a
    particular activity).
    '''
    name = sub(r'\s+', '', short_name)
    if activity_group:
        activity_group = ActivityGroup.from_name(s, activity_group)
        if activity_group.name != ALL: name = '%s.%s' % (name, sub(r'\s+', '', activity_group.name))
    return name


def add_diary_topic(s, name, sort, description=None, schedule=None):
    '''
    Add a root topic.

    DiaryTopics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A root topic is usually used as a header to group related children.
    For example, 'DailyDiary' to group diary entries (notes, weight, sleep etc), or 'Plan' to group training plans.
    '''
    return add(s, DiaryTopic(name=name, sort=sort, description=description, schedule=schedule))


def add_child_diary_topic(s, parent, name, sort, description=None, schedule=None):
    '''
    Add a child topic.

    DiaryTopics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A child topic is used to add additional structure to an existing topic.
    For example, the parent topic might be "injuries" and permanent, while children are defined for
    specific injuries with a schedule that gives start and end dates.
    '''
    return add(s, DiaryTopic(parent=parent, name=name, sort=sort, description=description, schedule=schedule))


def add_diary_topic_field(s, diary_topic, name, sort, type, description=None, units=None, summary=None, schedule=None,
                          model=None):
    '''
    Add a field and associated statistic to a topic entry.

    This is how the user can enter values into the diary.
    The field describes how the values are displayed in the diary.
    The statistic describes how the values are stored in the database.
    '''
    if diary_topic.id is None:
        s.flush()
    statistic_name = add(s, StatisticName(name=name, owner=DiaryTopic, statistic_journal_type=type,
                                          description=description, units=units, summary=summary,
                                          activity_group=ActivityGroup.from_name(s, ALL)))
    if model is None: model = {}
    field = add(s, DiaryTopicField(diary_topic=diary_topic, sort=sort, model=model, schedule=schedule,
                                   statistic_name=statistic_name))


def add_activity_topic(s, name, sort, description=None):
    '''
    Add a root topic.

    DiaryTopics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A root topic is usually used as a header to group related children.
    For example, 'DailyDiary' to group diary entries (notes, weight, sleep etc), or 'Plan' to group training plans.
    '''
    return add(s, ActivityTopic(name=name, sort=sort, description=description))


def add_child_activity_topic(s, parent, name, sort, description=None):
    '''
    Add a child topic.

    DiaryTopics are displayed in the diary.
    They can be permanent, or associated with some schedule.
    They can also be associated with fields (and so with statistics).

    A child topic is used to add additional structure to an existing topic.
    For example, the parent topic might be "injuries" and permanent, while children are defined for
    specific injuries with a schedule that gives start and end dates.
    '''
    return add(s, ActivityTopic(parent=parent, name=name, sort=sort, description=description))


def add_activity_topic_field(s, activity_topic, name, sort, type, activity_group,
                             description=None, units=None, summary=None, model=None):
    '''
    Add a field and associated statistic to a topic entry.

    This is how the user can enter values into the diary.
    The field describes how the values are displayed in the diary.
    The statistic describes how the values are stored in the database.
    '''
    if activity_topic and activity_topic.id is None:
        s.flush()
    # cannot simply add as this is also called during loading
    statistic_name = StatisticName.add_if_missing(s, name, type, units, summary, ActivityTopic,
                                                  activity_group=activity_group, description=description)
    if model is None: model = {}
    return add(s, ActivityTopicField(activity_topic=activity_topic, sort=sort, model=model,
                                     statistic_name=statistic_name))


def add_nearby(s, sort, activity_group, constraint, latitude, longitude, border=5,
               start='1970', finish='2999', height=10, width=10, fraction=1, constant=NEARBY_CNAME):
    '''
    Add a pipeline task (and related constant) to find nearby activities in a given geographic
    region (specified by latitude, longitude, width and height, all in degrees).
    '''
    log.debug(f'Adding nearby statistics for {constraint} / {activity_group.name}')
    nearby_constraint = name_constant(s, constraint, activity_group)
    constant = add_enum_constant(s, constant, Nearby,
                      {'constraint': nearby_constraint, 'activity_group': activity_group.name,
                       'border': border, 'start': start, 'finish': finish,
                       'latitude': latitude, 'longitude': longitude,
                       'height': height, 'width': width, 'fraction': fraction},
                      single=True, activity_group=activity_group, description='''
A region over which activities are candidates to be 'near' each other.  
This does not mean that all activities in this area are near to each other - 
only that activities outside will not be considered as candidates.
* Constraint is the name of the region.
* Activity_group identifies which activities are considered.
* Border is the radius (m) around GPS points for them to 'overlap' ('nearby' routes have a large number of 'ovelapping' points).
* Start and finish are dates between which the region is used.
* Latitude and longitude define the centre of the region (degrees).
* Height and width define the size of the region (degrees).
* Fraction reduces the number of points used to match two activities (increasing processing speed).
''')
    add_statistics(s, SimilarityCalculator, sort, nearby=constant.name,
                   owner_in=short_cls(ActivityCalculator), owner_out=short_cls(SimilarityCalculator))
    add_statistics(s, NearbyCalculator, sort, constraint=nearby_constraint,
                   owner_in=short_cls(SimilarityCalculator), owner_out=short_cls(NearbyCalculator))


def add_loader_support(s):
    '''
    Add 'dummy' value used by loader.
    '''
    log.debug('Adding dummy source')
    dummy_source = add(s, Dummy())
    dummy_name = add(s, StatisticName(name=DUMMY, owner=dummy_source,
                                      activity_group=ActivityGroup.from_name(s, ALL),
                                      statistic_journal_type=StatisticJournalType.STATISTIC))
