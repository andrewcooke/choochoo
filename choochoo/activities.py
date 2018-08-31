from glob import glob
from os import stat
from os.path import isdir, join

from sqlalchemy.orm.exc import NoResultFound
from urwid import Edit, Pile, Columns, connect_signal

from .args import PATH, ACTIVITY, EDIT_ACTIVITIES
from .fit.format.read import filtered_records
from .lib.io import tui
from .squeal.database import Database
from .squeal.tables.activity import Activity, FileScan, ActivityDiary
from .uweird.editor import EditorApp
from .uweird.factory import Factory
from .uweird.focus import MessageBar, FocusWrap
from .uweird.widgets import SquareButton, ColSpace


class ActivityWidget(FocusWrap):

    def __init__(self, log, tabs, bar, outer):
        self.__outer = outer
        factory = Factory(tabs=tabs, bar=bar)
        self.title = factory(Edit(caption='Title: '))
        self.sort = factory(Edit(caption='Sort: '))
        self.delete = SquareButton('Delete')
        delete = factory(self.delete, message='delete from database')
        self.reset = SquareButton('Reset')
        reset = factory(self.reset, message='reset from database')
        self.description = factory(Edit(caption='Description: ', multiline=True))
        super().__init__(
            Pile([self.title,
                  Columns([(20, self.sort),
                           ColSpace(),
                           (10, delete),
                           (9, reset)
                           ]),
                  self.description,
                  ]))

    def connect(self, binder):
        connect_signal(self.reset, 'click', lambda widget: binder.reset())
        connect_signal(self.delete, 'click', lambda widget: self.__on_delete(widget, binder))

    def __on_delete(self, _unused_widget, binder):
        binder.delete()
        self.__outer.remove(self)


@tui
def edit_activities(args, log):
    '''
# edit-activities

    ch2 edit-activities

The interactive editor for activities.  Allows addition, deletion and modification of activities.

Once added, activities can be imported and will appear in the diary.

To exit, alt-q (or, without saving, Alt-x).
    '''
    session = Database(args, log).session()
    EditorApp(log, session, MessageBar(), "Activities", ActivityWidget, Activity).run()


def add_file(log, session, activity_id, path):
    data, types, messages, records = filtered_records(log, path)
    diary = ActivityDiary()
    session.add(diary)
    for record in records:
        print(record)


def add_stats(log, session, activity_id, path):
    pass


def add_activity(args, log):
    '''
# add-activity

    ch2 add-activity ACTIVITY PATH

Read one or more (if PATH is a directory) FIT files and associated them with the given activity type.
    '''
    db = Database(args, log)

    activity = args[ACTIVITY][0]
    try:
        with db.session_context() as session:
            activity_id = session.query(Activity).filter(Activity.title == activity).one().id
    except NoResultFound:
        raise Exception('Activity "%s" is not defined - see ch2 %s' % (activity, EDIT_ACTIVITIES))

    path = args.path(PATH, index=0, rooted=False)
    if isdir(path):
        path = join(path, '*.fit')
    files = list(glob(path))
    if not files:
        raise Exception('No match for "%s"' % path)
    for file in files:
        with db.session_context() as session:
            try:
                scan = session.query(FileScan).filter(FileScan.path == file).one()
            except NoResultFound:
                scan = FileScan(path=file, last_scan=0)
                session.add(scan)
            last_modified = stat(file).st_mtime
            if last_modified > scan.last_scan:
                log.info('Scanning %s' % file)
                add_file(log, session, activity_id, file)
                add_stats(log, session, activity_id, file)
                scan.last_scan = last_modified
                session.flush()
            else:
                log.debug('Skipping %s (already scanned)' % file)
                session.expunge(scan)

