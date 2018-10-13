
from ...squeal.tables.config import DiaryPipeline


def build_display(log, session, factory, date):
    for cls, args, kargs in ((diary.cls, diary.args, diary.kargs)
                             for diary in session.query(DiaryPipeline).order_by(DiaryPipeline.sort).all()):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, **kargs)
