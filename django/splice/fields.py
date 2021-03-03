from django.db import models
from django.splice.splice import SpliceMixin
from django.splice.splicetypes import SpliceStr, SpliceInt
from django.splice.identity import TaintSource
from bitarray.util import int2ba, ba2int


# use Field's __class__.__qualname__ to find the corresponding Splice class
type_dict = {'SpliceIntegerField': SpliceInt,
             'SpliceCharField': SpliceStr}


class SpliceCreator(object):
    """Splice field descriptor object. It is like DeferredAttribute in Django source."""
    def __init__(self, field):
        self.field = field
        self.synthesized_field_name = "{}_synthesized".format(self.field.name)
        self.taint_field_name = "{}_taint".format(self.field.name)

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
            taints = getattr(obj, self.taint_field_name)
            # Convert from integer into bitarray
            ba = int2ba(taints, length=TaintSource.MAX_USERS, endian='big', signed=True)
            return cls.splicify(data,
                                trusted=False,
                                synthesized=getattr(obj, self.synthesized_field_name),
                                taints=ba)

    def __set__(self, obj, value):
        if isinstance(value, SpliceMixin):
            obj.__dict__[self.field.name] = value
            setattr(obj, self.synthesized_field_name, value.synthesized)
            # Convert the bitarray into integer
            taints = ba2int(value.taints, signed=True)
            setattr(obj, self.taint_field_name, taints)
        else:
            obj.__dict__[self.field.name] = self.field.to_python(value)


class SpliceFieldMixin(object):
    def contribute_to_class(self, cls, name, private_only=False):
        synthesized_field_name = "{}_synthesized".format(name)
        taint_field_name = "{}_taint".format(name)
        if not cls._meta.abstract and not hasattr(cls, synthesized_field_name):
            synthesized_field = models.BooleanField(default=False)
            # We must manually update creation_counter. Reference:
            # https://blog.elsdoerfer.name/2008/01/08/fuzzydates-or-one-django-model-field-multiple-database-columns/
            synthesized_field.creation_counter = self.creation_counter
            cls.add_to_class(synthesized_field_name, synthesized_field)

            taint_field = models.BigIntegerField(default=0)
            taint_field.creation_counter = self.creation_counter
            cls.add_to_class(taint_field_name, taint_field)
        super().contribute_to_class(cls, name)
        setattr(cls, name, SpliceCreator(self))


class SpliceIntegerField(SpliceFieldMixin, models.IntegerField):
    pass


class SpliceCharField(SpliceFieldMixin, models.CharField):
    pass


if __name__ == "__main__":
    pass
