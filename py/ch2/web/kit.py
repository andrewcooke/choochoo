from logging import getLogger

from werkzeug.utils import redirect

from ..jupyter.load import create_notebook
from ..jupyter.utils import get_template


log = getLogger(__name__)


class Kit:

    @staticmethod
    def read_diary(request, s, date):
        schedule, date = parse_date(date)
        if schedule == 'd':
            data = read_date(s, date)
        else:
            data = read_schedule(s, Schedule(schedule), date)
        return Response(dumps(rewrite_db(list(data))))

