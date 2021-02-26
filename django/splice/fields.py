from django.db import models
from django.splice.splicetypes import SpliceStr, SpliceInt


# use Field's __class__.__qualname__ to find the corresponding Splice class
type_dict = {'SpliceIntegerField': SpliceInt,
             'SpliceCharField': SpliceStr}


class SpliceCreator(object):
    """Splice field descriptor object. It is like DeferredAttribute in Django source."""
    def __init__(self, field):
        self.field = field
        self.synthesized_field_name = "{}_synthesized".format(self.field.name)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance')

        data = obj.__dict__[self.field.name]
        if data is None:
            return None
        else:
            cls = type_dict.get(self.field.__class__.__qualname__)
            if cls is None:
                raise AttributeError('Cannot find any registered Splice data type for {}'
                                     .format(self.field.__class__.__qualname__))
            return cls.splicify(data, trusted=False, synthesized=getattr(obj, self.synthesized_field_name))

    def __set__(self, obj, value):
        if isinstance(value, SpliceInt):
            obj.__dict__[self.field.name] = value
            setattr(obj, self.synthesized_field_name, value.synthesized)
        else:
            obj.__dict__[self.field.name] = self.field.to_python(value)


class SpliceMixin(object):
    def contribute_to_class(self, cls, name, private_only=False):
        synthesized_field_name = "{}_synthesized".format(name)
        if not cls._meta.abstract and not hasattr(cls, synthesized_field_name):
            synthesized_field = models.BooleanField(default=False)
            cls.add_to_class(synthesized_field_name, synthesized_field)
        super().contribute_to_class(cls, name)
        setattr(cls, name, SpliceCreator(self))


class SpliceIntegerField(SpliceMixin, models.IntegerField):
    pass


class SpliceCharField(SpliceMixin, models.CharField):
    pass


if __name__ == "__main__":
    pass
