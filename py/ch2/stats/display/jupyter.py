
from . import ActivityJournalDelegate
from .nearby import fmt_nearby, nearby_any_time
from ...diary.database import COMPARE_LINKS
from ...diary.model import text, link, optional_text
from ...lib import time_to_local_time, to_time
from ...lib.date import YMD_HM, HM, format_date


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
    def read_schedule(self, s, date, schedule):
        finish = schedule.next_frame(date)
        yield link('All Activities', db=(format_date(date), format_date(finish)))
