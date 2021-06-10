"""
If we use cell-level tainting in DB, every field should inherit from SpliceFieldMixin
to override the default contribute_to_class() method, which creates additional database
columns dynamically for storing taints and tags, and assigns a SpliceDescriptor
to the field object, so that when the field is accessed from the model instance, the
SpliceDescriptor is called to construct the field object with taints/tags from the
additional columns accordingly. This SpliceFieldMixin is useful for cell-level tainting only.
"""

from django.db import models
from django.splice.splice import add_taints
from django.splice.splicetypes import SpliceMixin, SpliceStr, SpliceInt, SpliceFloat, SpliceDatetime
from django.splice.identity import to_int, to_bitarray


# use Field's __class__.__qualname__ to find the corresponding Splice class
type_dict = {'SpliceIntegerField': SpliceInt,
             'SplicePositiveIntegerField': SpliceInt,
             'SplicePositiveSmallIntegerField': SpliceInt,
             'SpliceCharField': SpliceStr,
             'SpliceSlugField': SpliceStr,
             'SpliceEmailField': SpliceStr,
             'SpliceTextField': SpliceStr,
             'SpliceGenericIPAddressField': SpliceStr,
             'SpliceFloatField': SpliceFloat,
             'SpliceDateTimeField': SpliceDatetime,
             }


class SpliceDescriptor(object):
    """
    Splice field descriptor. It is similar to DeferredAttribute
    (db.models.query_utils) in Django. This allows model's field
    access to obtain its taints and tags. All non-relational,
    primitive-typed field should use this descriptor to obtain
    taints. Django defines its own descriptors for relational field,
    which Splice modifies for taint propagation directly.
    """
    def __init__(self, field):
        self.field = field
        self.synthesized_field_name = "{}_synthesized".format(self.field.name)
        self.taint_field_name = "{}_taint".format(self.field.name)

    def __get__(self, instance, type=None):
        if instance is None:
            raise AttributeError('taints can be laundered without instance')

        data = instance.__dict__
        val = data[self.field.name]
        if val is None:
            # val can be None, for example, when deletion has occurred in the past
            # print("SpliceDescriptor.__get__({}): value is None".format(self.field.name))
            return None
        taints = getattr(instance, self.taint_field_name)
        synthesized = getattr(instance, self.synthesized_field_name)
        # A model instance might get its data after it is constructed from ModelForm
        # (e.g., to perform validation). Since the data is not retrieved from DB, it
        # is already a Splice-aware type; therefore, we don't need to cast it at all.
        # However, we may need to update its taint and tag (this update usually is not
        # useful since val's taint/tag should mostly like be the same as in the DB;
        # however, when initializing User in django_lfs.lfs.customer.views.login, we
        # need to update user fields' taints properly).
        if isinstance(val, SpliceMixin):
            add_taints(val, to_bitarray(taints))
            val.synthesized = synthesized
            if synthesized:
                val.trusted = False
            return val
        else:
            cls = type_dict.get(self.field.__class__.__qualname__)
            if cls is None:
                raise AttributeError('Cannot find any registered Splice data type for {}'
                                     .format(self.field.__class__.__qualname__))
            return cls.splicify(val,
                                # NOTE: Data stored in a database is always considered *untrusted*
                                #       (regardless of whether the value is synthesized) because
                                #       of the possibility that the value can be synthesized. Marking
                                #       data untrusted allows the type system to always check before use.
                                trusted=False,
                                synthesized=synthesized,
                                taints=to_bitarray(taints),
                                constraints=[])

    def __set__(self, instance, value):
        if isinstance(value, SpliceMixin):
            instance.__dict__[self.field.name] = value
            setattr(instance, self.synthesized_field_name, value.synthesized)
            setattr(instance, self.taint_field_name, to_int(value.taints))
        else:
            instance.__dict__[self.field.name] = self.field.to_python(value)


class SpliceFieldMixin(object):
    """
    Override contribute_to_class to create two additional fields when
    a field is created. One field is a synthesized field and the other
    is a taint field.
    """
    def contribute_to_class(self, cls, name, private_only=False):
        synthesized_field_name = "{}_synthesized".format(name)
        taint_field_name = "{}_taint".format(name)
        if not cls._meta.abstract:
            # For migration to work correctly, we must check if our dynamically added
            # fields have already been added to the table by the migration runner.
            # Otherwise, we may see "django.db.utils.OperationalError: duplicate column name:..."
            # See reference: https://stackoverflow.com/a/46174975/9632613
            # Note that dynamically adding new fields through a field is not officially
            # supported by Django: https://code.djangoproject.com/ticket/22555, but we
            # can make it work for us.
            if not hasattr(cls, synthesized_field_name):
                synthesized_field = models.BooleanField(default=False)
                # We must manually update creation_counter. Reference:
                # https://blog.elsdoerfer.name/2008/01/08/fuzzydates-or-one-django-model-field-multiple-database-columns/
                synthesized_field.creation_counter = self.creation_counter
                cls.add_to_class(synthesized_field_name, synthesized_field)
            if not hasattr(cls, taint_field_name):
                taint_field = models.BigIntegerField(default=0)
                taint_field.creation_counter = self.creation_counter
                cls.add_to_class(taint_field_name, taint_field)
        super().contribute_to_class(cls, name)
        setattr(cls, name, SpliceDescriptor(self))


# Convert existing Django fields to be Splice-aware (dynamically create those classes)
SpliceIntegerField = type("SpliceIntegerField", (SpliceFieldMixin, models.IntegerField,), {})
SplicePositiveIntegerField = type("SplicePositiveIntegerField", (SpliceFieldMixin, models.PositiveIntegerField,), {})
SpliceCharField = type("SpliceCharField", (SpliceFieldMixin, models.CharField,), {})
SpliceEmailField = type("SpliceEmailField", (SpliceFieldMixin, models.EmailField,), {})
SpliceSlugField = type("SpliceSlugField", (SpliceFieldMixin, models.SlugField,), {})
SplicePositiveSmallIntegerField = type("SplicePositiveSmallIntegerField",
                                       (SpliceFieldMixin, models.PositiveSmallIntegerField,), {})
SpliceFloatField = type("SpliceFloatField", (SpliceFieldMixin, models.FloatField), {})
SpliceTextField = type("SpliceTextField", (SpliceFieldMixin, models.TextField), {})
SpliceDateTimeField = type("SpliceDateTimeField", (SpliceFieldMixin, models.DateTimeField), {})
SpliceGenericIPAddressField = type("SpliceGenericIPAddressField", (SpliceFieldMixin, models.GenericIPAddressField), {})
