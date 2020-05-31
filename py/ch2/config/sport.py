from itertools import zip_longest
from json import loads
from logging import getLogger

from ..lib.utils import clean
from ..names import SPORT_CYCLING, SPORT_RUNNING, SPORT_SWIMMING, SPORT_WALKING, SPORT_GENERIC, SPORT_MAP
from ..sql import KitItem, ActivityGroup
from ..sql.tables.constant import ValidateError, Validate, Constant

log = getLogger(__name__)


class SportMap:

    SPORTS = [clean(s) for s in (SPORT_CYCLING, SPORT_RUNNING, SPORT_SWIMMING, SPORT_WALKING, SPORT_GENERIC)]

    def __init__(self, json):
        '''
        the json representation is a list of string triplets: [(sport, kit, group), ...]
        where sport matches the sport in the FIT file, kit matches any kit specified by the user on upload,
        and group identifies the activity group that will include the activity.
        first match 'wins' and None for sport or kit is a wildcard.
        None for group is equivalent to ALL.
        there is an implicit final entry of (None, None, None) which matches anything to ALL.
        '''
        if isinstance(json, str):
            json = loads(json)
        self.__json = json

    def add(self, s, error=True):
        self.validate(s, error=error)
        if s.query(Constant).filter(Constant.name == SPORT_MAP).count():
            raise Exception(f'Constant {SPORT_MAP} already exists')
        constant = Constant(name=SPORT_MAP, )


    class Validator(Validate):

        def __init__(self, error=True):
            self.__error = error

        def validate(self, s, constant, sjournal):
            try:
                json = loads(sjournal.value)
            except Exception as e:
                raise ValidateError('Could not unpack JSON value for %s from "%s": %s' %
                                    (sjournal.value, constant.name, e))
            SportMap.validate_json(s, json, error=self.__error)

    def validate(self, s, error=True):
        self.validate_json(s, self.__json, error=error)

    @classmethod
    def validate_json(cls, s, json, error=True):
        try:
            for entries in json:
                for entry, validator in zip_longest(entries,
                                                    (cls.validate_sport, cls.validate_kit, cls.validate_group)):
                    try:
                        validator(s, entry)
                    except ValidateError as e:
                        if error:
                            log.error(e)
                            raise
                        else:
                            log.warning(e)
        except ValidateError:
            raise
        except Exception as e:
            log.error(f'Cannot validate {json}: {e}')
            # this is always an error - we need to be able to parse the thing
            raise

    @classmethod
    def validate_sport(cls, s, sport):
        if clean(sport) not in cls.SPORTS:
            raise ValidateError(f'Unknown sport {sport}')

    @classmethod
    def validate_kit(cls, s, kit):
        if not s.query(KitItem).filter(KitItem.name == kit).count():
            raise ValidateError(f'Unknown kit {kit}')

    @classmethod
    def validate_group(cls, s, group):
        if not s.query(ActivityGroup).filter(ActivityGroup.name == group).count():
            raise ValidateError(f'Unknown group {group}')