
import datetime as dt
from abc import ABC, abstractmethod
from re import sub, compile

from .date import parse_date, format_date


# my calculations are done relative to the unix epoch.  the "gregorian ordinal"
# is relative to year 1, but i have no idea how the details of that work.  i
# guess i could do everything in gregorian ordinals simply projecting back the
# current weeks / months and it would be equivalent, but i'd need to tweak the
# week offset by hand (here it's because 1970-01-01 is a thursday).

WEEK_OFFSET = 3
EPOCH_OFFSET = dt.date(1970, 1, 1).toordinal()
DOW = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


class Specification:
    """
    Parse a spec and reduce it to a normalized form (available through __str__()).
    """

    DOW_INDEX = dict((day, i) for i, day in enumerate(DOW))

    def __init__(self, spec):
        try:
            spec = sub(r'\s+', '', spec)
            spec = spec.lower()
            m = compile(r'^([\d\-/]*[dwm])(\[[^\]]*\])?([\d\-]*)$').match(spec)
            frame, locations, range = m.group(1), m.group(2), m.group(3)
            self.__parse_frame(frame)
            self.__parse_locations(locations)
            self.__parse_range(range)
        except:
            raise Exception('Cannot parse %s' % spec)

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
                return int(location[:-3]), self.DOW_INDEX[location[-3:]]
            else:
                return 1, self.DOW_INDEX[location]
        else:
            return int(location)

    def __parse_locations(self, locations):
        if locations:
            locations = locations[1:-1]
        if locations:
            self.locations = list(map(self.__parse_location, locations.split(',')))
        else:
            self.locations = [1]

    def __parse_range(self, range):
        if range:
            m = compile(r'^(\d+-\d+-\d+)?-(\d+-\d+-\d+)?$').match(range)
            if m:
                self.__start = parse_date(m.group(1)) if m.group(1) else None
                self.__finish = parse_date(m.group(2)) if m.group(2) else None
            else:
                self.__start = parse_date(range)
                self.__finish = self.__start
        else:
            self.__start, self.__finish = None, None

    def __str__(self):
        return '%d/%d%s[%s]%s' % (self.offset, self.repeat, self.frame_type,
                                  self.__str_locations(), self.__str_ranges())

    def __str_locations(self):
        return ','.join(map(self.__str_location, self.locations))

    def __str_location(self, location):
        try:
            return '%d%s' % (location[0], DOW[location[1]])
        except:
            return str(location)

    def __str_ranges(self):
        if self.__start is None and self.__finish is None:
            return ''
        elif self.__start == self.__finish:
            return self.__str_range(self.__start)
        else:
            return '%s-%s' % (self.__str_range(self.__start), self.__str_range(self.finish))

    def __str_range(self, range):
        if range is None:
            return ''
        else:
            return format_date(range)

    def frame(self):
        return {'d': Day, 'w':Week, 'm':Month}[self.frame_type](self)

    # allow range to be set separately (allows separate column in database, so
    # we can select for valid reminders).

    def __parse_null_date(self, date):
        if date is None:
            return date
        try:
            return parse_date(date)
        except TypeError:
            try:
                dt.date.fromordinal(int(date))
            except TypeError:
                return date

    def __set_start(self, date):
        self.__start = self.__parse_null_date(date)

    def __set_finish(self, date):
        self.__finish = self.__parse_null_date(date)

    start = property(lambda self: self.__start, __set_start)
    finish = property(lambda self: self.__finish, __set_finish)


class DateOrdinals:

    def __init__(self, date_or_text):
        try:
            date = parse_date(date_or_text)
        except:
            date = date_or_text
        self.m = 12 * (date.year - 1970) + date.month - 1
        self.d = (date - dt.date(1970, 1, 1)).days
        self.w = (self.d + WEEK_OFFSET) // 7  # 1970-01-01 is Th
        self.ordinals = vars(self)
        self.date = date

    def __str__(self):
        return format_date(self.date)


class Frame(ABC):

    def __init__(self, spec):
        self.spec = spec

    def at_frame(self, ordinals):
        if self.spec.start is None or self.spec.start <= ordinals.date:
            if self.spec.finish is None or ordinals.date <= self.spec.finish:
                ordinal = ordinals.ordinals[self.spec.frame_type]
                return self.spec.offset == ordinal % self.spec.repeat
        return False

    def at_location(self, ordinals):
        for date in self.locations_in_frame(ordinals):
            if date == ordinals.date:
                return True
        return False

    @abstractmethod
    def locations_in_frame(self, ordinals):
        pass


class Day(Frame):

    def locations_in_frame(self, ordinals):
        if self.at_frame(ordinals):
            for location in self.spec.locations:
                if location == 1:
                    yield ordinals.date
                else:
                    try:
                        n, day = location
                        if n == 1 and ordinals.date.weekday() == day:
                            yield ordinals.date
                    except TypeError:
                        pass


class Week(Frame):

    def locations_in_frame(self, ordinals):
        if self.at_frame(ordinals):
            ordinal = 7 * ordinals.w - WEEK_OFFSET + EPOCH_OFFSET
            for location in self.spec.locations:
                try:
                    if 1 <= location <= 7:
                        yield dt.date.fromordinal(ordinal + location - 1)
                except TypeError:
                    n, d = location
                    if n == 1:
                        yield dt.date.fromordinal(ordinal + d)


class Month(Frame):

    def locations_in_frame(self, ordinals):
        if self.at_frame(ordinals):
            m = ordinals.m
            day_start = dt.date(1970 + m // 12, 1 + m % 12, 1)
            dow_start = day_start.weekday()
            day_end = dt.date(1970 + (m+1) // 12, 1 + (m+1) % 12, 1) - dt.timedelta(days=1)
            for location in self.spec.locations:
                try:
                    if 1 <= location <= day_end.day:
                        yield day_start + dt.timedelta(days=location-1)
                except TypeError:
                    n, d = location
                    d -= dow_start
                    if d < 0: d += 7
                    d += (n-1) * 7
                    if 0 <= d < day_end.day:
                        yield day_start + dt.timedelta(days=d)
