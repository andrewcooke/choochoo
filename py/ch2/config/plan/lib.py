
class ORMUtils:

    def _get_or_create(self, session, cls, **kargs):
        query = session.query(cls)
        for (name, value) in kargs.items():
            query = query.filter(getattr(cls, name) == value)
        instance = query.one_or_none()
        if instance is None:
            instance = cls(**kargs)
            session.add(instance)
        return instance