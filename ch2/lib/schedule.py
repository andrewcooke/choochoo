
import datetime as dt
from abc import ABC, abstractmethod
from calendar import monthrange
from re import sub, compile, match

from .date import to_date, format_date, add_date, local_date_to_time, time_to_local_date

# my calculations are done relative to the unix epoch.  the "gregorian ordinal"
# is relative to year 1, but i have no idea how the details of that work.  i
# guess i could do everything in gregorian ordinals simply projecting back the
# current weeks / months and it would be equivalent, but i'd need to tweak the
# week offset by hand (here it's because 1970-01-01 is a thursday).

ZERO = dt.date(1970, 1, 1)
WEEK_OFFSET = 3
EPOCH_OFFSET = ZERO.toordinal()
DOW = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


class Schedule:
    """
    Parse a spec and reduce it to a normalized form (available through __str__()).

    Offset can shift whole "units" only.  So 3w can start on *any* Monday,
    depending on the offset data, but the week always starts on a Monday.

    Note that dates are dates, not datetimes (times).
    """

    DOW_INDEX = dict((day, i) for i, day in enumerate(DOW))

    def __init__(self, spec):
        self.__start = None  # dt.date visible via self.start (inclusive)
        self.__finish = None  # dt.date visible via self.finish (exclusive)
        self.offset = None  # int (units of frame relative to start of unix epoch)
        self.repeat = None  # int (units of frame)
        self.frame_type = None  # character (as spec, so all lower case)
        self.locations = None  # list of day offsets or (week, dow) tuples (if empty, all dates)
        try:
            spec = '' if spec is None else spec
            spec = sub(r'\s+', '', spec)
            spec = spec.lower()
            m = match(r'^([\d\-/]*[dwmy])?(\[[^\]]*\])?([\d\-]*)$', spec)
            frame, locations, range = m.group(1), m.group(2), m.group(3)
            self.__parse_frame(frame)
            self.__parse_locations(locations)
            self.__parse_range(range)
        except:
            raise Exception('Cannot parse "%s" (%s)' % (spec, type(spec)))
        if self.locations and self.frame_type == 'y':
            raise Exception('Locations not supported in yearly schedules')
        self.__frame = self.frame_class()(self)

    def __date_to_ordinal(self, text):
        return DateOrdinals(text).ordinals[self.frame_type]

    @staticmethod
    def __parse_ordinal(text):
        if text.isdecimal():
            return int(text), 'd'
        elif len(text) > 1:
            return int(text[:-1]), text[-1]
        else:
            return 1, text

    def __parse_frame(self, frame):
        if frame is None:
            frame = 'd'
        if '/' in frame:
            offset, rft = frame.split('/')
        else:
            offset, rft = '0', frame
        self.repeat, self.frame_type = self.__parse_ordinal(rft)
        if '-' in offset:
            self.offset = self.__date_to_ordinal(offset)
        else:
            self.offset = int(offset)
        self.offset %= self.repeat

    def __parse_location(self, location):
        if location[-3:] in DOW:
            if len(location) > 3:
                if self.frame_type == 'd':
                    raise Exception('Numbered locations in daily frames not supported')
                return int(location[:-3]), self.DOW_INDEX[location[-3:]]
            else:
                return 0, self.DOW_INDEX[location]  # 0 means all weeks (in a month)
        else:
            return int(location)

    def __parse_locations(self, locations):
        if locations:
            locations = locations[1:-1]  # drop []
        if locations:
            if self.frame_type == 'y':
                raise Exception('Locations in yearly frames not supported')
            self.locations = sorted(map(self.__parse_location, locations.split(',')), key=self.__key)
        else:
            self.locations = []  # all

    def __key(self, location):
        if isinstance(location, int):
            return (-1, location)
        else:
            return location

    def __parse_range(self, range):
        if range:
            m = compile(r'^(\d+-\d+-\d+)?-(\d+-\d+-\d+)?$').match(range)
            if m:
                self.__start = to_date(m.group(1)) if m.group(1) else None
                self.__finish = to_date(m.group(2)) if m.group(2) else None
            else:
                # if a single value is given then it is the start with an implicit finish that
                # is the day after (so a single day, since finish is exclusive)
                self.__start = to_date(range)
                self.__finish = self.__start + dt.timedelta(days=1)
        else:
            self.__start, self.__finish = None, None

    def __str__(self):
        return '%s%s%s' % (self.__str_offset(), self.__str_locations(), self.__str_ranges())

    def __str_offset(self):
        repeat = '%d' % self.repeat if self.repeat > 1 else ''
        if self.offset:
            return '%d/%s%s' % (self.offset, repeat, self.frame_type)
        elif repeat or self.frame_type != 'd' or not (self.start or self.finish):
            return '%s%s' % (repeat, self.frame_type)
        else:
            return ''

    def __str_locations(self):
        if self.locations:
            return '[%s]' % ','.join(map(self.__str_location, self.locations))
        else:
            return ''

    def __str_location(self, location):
        try:
            if location[0]:
                return '%d%s' % (location[0], DOW[location[1]])
            else:
                return DOW[location[1]]
        except:
            return str(location)

    def __str_ranges(self):
        if self.__start is None and self.__finish is None:
            return ''
        elif self.__start and self.__start + dt.timedelta(days=1) == self.__finish:
            return self.__str_range(self.__start)
        elif self.__start and not self.__finish:
            return '%s-' % self.__str_range(self.__start)
        elif self.__finish and not self.__start:
            return '-%s' % self.__str_range(self.__finish)
        else:
            return '%s-%s' % (self.__str_range(self.__start), self.__str_range(self.finish))

    def __str_range(self, range):
        if range is None:
            return ''
        else:
            return format_date(range)

    def frame_class(self):
        return {'d': Day, 'w': Week, 'm': Month, 'y': Year}[self.frame_type]

    # allow range to be set separately (allows separate column in database, so
    # we can select for valid reminders).

    def __set_start(self, date):
        self.__start = to_date(date, none=True)

    def __set_finish(self, date):
        self.__finish = to_date(date, none=True)

    start = property(lambda self: self.__start, __set_start)
    finish = property(lambda self: self.__finish, __set_finish)

    def in_range(self, date):
        date = to_date(date)
        return (self.start is None or date >= self.start) and \
               (self.finish is None or date < self.finish)

    def describe(self, compact=False):
        if compact:
            text = self.frame_type
        else:
            text = '%s' % self.frame_class().__name__
        if self.repeat > 1:
            text = '%d%ss' % (self.repeat, text)
        text = '%s%s' % (text, self.__str_locations())
        return text

    def __in_range_or_none(self, date):
        if self.in_range(date):
            return date
        else:
            return None

    def start_of_frame(self, date):
        return self.__in_range_or_none(self.__frame.start_of_frame(date))

    def next_frame(self, date):
        return self.__in_range_or_none(self.__frame.start_of_frame(date) +
                                       dt.timedelta(days=self.frame_length_in_days(date)))

    def frame_length_in_days(self, date):
        return self.__frame.length_in_days(date)

    def locations_from(self, start):
        '''
        Locations in successive frames (ordered), starting at the give date.
        '''
        yield from self.__frame.locations_from(start)
        while True:
            start = self.next_frame(start)
            if start:
                yield from self.__frame.locations_from(start)
            else:
                return

    def at_location(self, date):
        return self.__frame.at_location(date)

    @classmethod
    def normalize(cls, spec):
        return str(Schedule(spec))

    @classmethod
    def include(cls, parent, child):
        '''
        Extend the parent (creating if necessary) to include the child.
        '''
        if parent is None:
            parent = Schedule('')

        def apply_with_none(f, a, b):
            if a:
                if b:
                    return f(a, b)
                else:
                    return a
            else:
                if b:
                    return b
                else:
                    return None

        parent.start = apply_with_none(min, parent.start, child.start)
        parent.finish = apply_with_none(max, parent.finish, child.finish)
        return parent


class DateOrdinals:

    def __init__(self, date):
        date = to_date(date)
        self.y = date.year - 1970
        self.m = 12 * self.y + date.month - 1
        self.d = (date - dt.date(1970, 1, 1)).days
        day = self.d + WEEK_OFFSET
        self.w = day // 7  # 1970-01-01 is Th
        self.dow = day % 7
        self.date = date
        self.ordinals = vars(self)

    def __str__(self):
        return format_date(self.date)


class Frame(ABC):

    def __init__(self, schedule):
        self.schedule = schedule

    def start_of_frame(self, date):
        '''
        The start date for the frame that includes or precedes the given date
        (ignoring range).
        '''
        date = DateOrdinals(date)
        n = (date.ordinals[self.schedule.frame_type] - self.schedule.offset) // self.schedule.repeat
        zero = add_date(self.zero, (self.schedule.offset, self.schedule.frame_type))
        return add_date(zero, (n * self.schedule.repeat, self.schedule.frame_type))

    def locations_from(self, start):
        '''
        Locations in a single frame, starting at the give date
        (so if the date isn't at the start of the frame you might not get all locations).
        '''
        start = to_date(start)
        frame = self.start_of_frame(start)
        ordinals = DateOrdinals(frame)
        for delta in self._location_offsets(ordinals.dow, self.length_in_days(start)):
            date = frame + dt.timedelta(days=delta)
            if self.schedule.in_range(date) and date >= start:
                yield date

    def _location_offsets(self, dow, limit):
        '''
        Generate offsets into frame for locations specified.
        Returns ordered values in [0, limit).
        '''
        # in future we could cache these for efficiency?
        # this should check against lower (0) and upper bounds (limit), but not range
        # or start value passed to dates()
        if self.schedule.locations:
            # locations may not be ordered, but is finite, so calculate a week in a batch
            # this guarantees that the offsets are ordered and unique (needed by dates())
            for week in range(1 + (dow + limit - 1) // 7):
                days = set()
                for location in self.schedule.locations:
                    if isinstance(location, int):
                        if 7*(week+1) >= dow + location > 7*week and location <= limit:
                            days.add(location - 1)
                    else:
                        n, day = location
                        if n and day < dow:
                            n += 1  # months only - numbering is not per week, but consecutive
                        if (n == 0 or week + 1 == n) and 0 <= week * 7 + day - dow < limit:
                            days.add(week*7 + day - dow)
                yield from sorted(days)
        else:
            yield from range(limit)

    def at_location(self, date):
        '''
        Does the given day coincide with the specification?
        '''
        try:
            date = to_date(date)
            return self.schedule.in_range(date) and date == next(self.locations_from(date))
        except StopIteration:
            return False

    @abstractmethod
    def length_in_days(self, date):
        '''
        The duration of a single frame containing the given date, in days.
        '''
        pass


class Day(Frame):

    zero = ZERO

    def length_in_days(self, date):
        return self.schedule.repeat


class Week(Frame):

    zero = ZERO - dt.timedelta(days=WEEK_OFFSET)

    def length_in_days(self, date):
        return self.schedule.repeat * 7


class Month(Frame):

    zero = ZERO

    def length_in_days(self, date):
        return monthrange(date.year, date.month)[1]


class Year(Frame):

    zero = ZERO

    def length_in_days(self, date):
        return (dt.date(date.year+1, 1, 1) - dt.date(date.year, 1, 1)).days

    def at_location(self, date):
        # locations not supported, so ignore for efficiency
        return self.schedule.in_range(date)
