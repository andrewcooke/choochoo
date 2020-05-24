
from .nearby import fmt_nearby, nearby_any_time
from ..utils import ActivityJournalDelegate
from ....diary.model import text, link, optional_text, COMPARE_LINKS
from ....lib import time_to_local_time
from ....lib.date import format_date


class JupyterDelegate(ActivityJournalDelegate):

    @optional_text('Jupyter', tag='jupyter-activity')
    def read_journal_date(self, s, ajournal, date):
        links = [link('None', db=(time_to_local_time(ajournal.start), None, ajournal.activity_group.name))] + \
                [link(fmt_nearby(ajournal2, nb),
                      db=(time_to_local_time(ajournal.start), time_to_local_time(ajournal2.start), ajournal.activity_group.name))
                 for ajournal2, nb in nearby_any_time(s, ajournal)]
        yield [text('Compare to', tag=COMPARE_LINKS)] + links
        yield link('All Similar', db=(time_to_local_time(ajournal.start), ajournal.activity_group.name))

    @optional_text('Jupyter', tag='jupyter-activity')
    def read_interval(self, s, interval):
        yield link('All Activities', db=(format_date(interval.start), format_date(interval.finish)))

