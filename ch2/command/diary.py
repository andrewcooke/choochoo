
import datetime as dt

from sqlalchemy import or_

from .args import DATE
from ..lib.date import to_date
from ..squeal.database import Database
from ..squeal.tables.topic import Topic


# @tui
def diary(args, log):
    '''
# diary

    ch2 diary [date]

The date can be an absolute day or the number of days previous.  So `ch2 diary 1` selects yesterday.

The daily diary.  Enter information here.

To exit, alt-q (or, without saving, alt-x).
    '''
    date = args[DATE]
    if not date:
        date = dt.date.today()
    else:
        try:
            date = to_date(date)
        except:
            date = dt.date.today() - dt.timedelta(days=int(date))
    db = Database(args, log)
    render(log, db, date)

def render(log, db, date):
    with db.session_context() as s:
        root_topics = [topic for topic in
                       s.query(Topic).
                           filter(Topic.parent == None,
                                  or_(Topic.start <= date, Topic.start == None),
                                  or_(Topic.finish >= date, Topic.finish == None)).
                           order_by(Topic.sort).all()
                       if topic.specification().in_range(date)]
        print(root_topics)
        for topic in root_topics:
            topic.populate(s, date)
            for field in topic.fields:
                print(field)
                print(topic.journal.fields[field])
                print(field.display_cls(log, s, topic.journal.fields[field], *field.display_args))
