"""
If we use row-level tainting in DB, every field should inherit from SpliceFieldMixin
to override the default contribute_to_class() method, which assigns a SpliceDescriptor
to the field object, so that when the field is accessed from the model instance, the
SpliceDescriptor is called to propagate taints/tags to the field object accordingly.
This SpliceFieldMixin is useful for row-level tainting only.
"""

from django.splice.splice import SpliceMixin
from django.splice.splicetypes import SpliceStr, SpliceInt
from django.splice.identity import to_bitarray


# use Field's __class__.__qualname__ to find the corresponding Splice class
type_dict = {'IntegerField': SpliceInt,
             'CharField': SpliceStr,
             'SlugField': SpliceStr,}


class SpliceDescriptor(object):
    """
    Splice field descriptor object. It is similar to DeferredAttribute
    (db.models.query_utils) in Django. This allows model instance's taint
    to "propagate" to its field. All non-relational, primitive-typed
    field should use this descriptor to obtain taints. Django defines
    its own descriptors for relational field, which Splice modifies for
    taint propagation directly.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, type=None):
        if instance is None:
            raise AttributeError('taints can be laundered without instance')

        data = instance.__dict__
        val = data[self.field.name]
        if val is None:
            print("SpliceDescriptor.__get__({}): value is None".format(self.field.name))
            return None
        # A model instance might get its data after it is constructed from ModelForm
        # (e.g., to perform validation). Since the data is not retrieved from DB, it
        # is already a Splice-aware type; therefore, we don't need to cast it at all.
        elif isinstance(val, SpliceMixin):
            return val
        else:
            cls = type_dict.get(self.field.__class__.__qualname__)
            if cls is None:
                raise AttributeError('Cannot find any registered Splice data type for {}'
                                     .format(self.field.__class__.__qualname__))
            # All models should inherit from SpliceDB to be Splice-aware
            # All model instance inherited from SpliceDB has a "taints" column.
            taints = getattr(instance, "taints", 0)
            # All model instance inherited from SpliceDB also has "trusted" and "synthesized" columns.
            trusted = getattr(instance, "trusted", True)
            synthesized = getattr(instance, "synthesized", False)
            # Convert from integer into bitarray (model instance's taints are integer)
            tba = to_bitarray(taints)
            return cls.splicify(val,
                                trusted=trusted,
                                synthesized=synthesized,
                                taints=tba)

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = self.field.to_python(value)


class SpliceFieldMixin(object):
    """
    All non-relational model fields should inherit from this mixin
    to add a descriptor to the field. This is done during the
    contribute_to_class call when models are being setup.
    """
    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name)
        setattr(cls, name, SpliceDescriptor(self))
