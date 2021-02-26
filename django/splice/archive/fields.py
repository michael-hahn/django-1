from django.core.exceptions import ValidationError
from django.db import models


def splice_attribute(owner_field):
    def _make_property(self, field_name):
        def _get_val(self, default=None):
            return getattr(self.instance, field_name, default)

        def _set_val(self, value):
            return setattr(self.instance, field_name, value)

        return property(_get_val, _set_val)

    class SpliceFieldInstance(object):
        """
        Represents a single instance of a SpliceFieldInstance on an object, by
        keeping track of both a reference to the parent instance and a reference
        to the MultiColumnField-derived class. This allows for "natural" access
        to the subfield values by using properties.
        """
        def __init__(self, instance, field):
            self.instance = instance
            self.field = field
            self.names = owner_field.names

            for name in self.names:
                prop = _make_property(self, self.field.field_names[name])
                setattr(SpliceFieldInstance, name, prop)

        def to_dict(self):
            d = {}
            for name in self.names:
                d[name] = getattr(self.instance, self.field.field_names[name], None)
            return d

        def __repr__(self):
            return self.field.instance_repr(self)

    return SpliceFieldInstance


class MultiColumnField(models.Field):
    """
    A field containing multiple sub-fields and spanning multiple columns.
    Reference: https://gist.github.com/gipi/2401143#file-gistfile1-py.
    """
    def __init__(self, *args, **kwargs):
        if not self.fields:
            self.fields = kwargs.pop('fields', None)
        if not self.fields:
            raise ValidationError("no fields attribute or argument provided")
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, private_only=False):
        self.name = name
        self.names = self.fields.keys()
        self.field_names = {}

        # Add all of the "real" fields to the class,
        # and cache the calculated field names
        for suffix, field in self.fields.items():
            field_name = "%s_%s" % (self.name, suffix)
            self.field_names[suffix] = field_name
            cls.add_to_class(field_name, field)

        # Generate SpliceAttribute for this MCF-derived class
        self.splice_attribute = splice_attribute(self)

        # Add this field as a class member
        setattr(cls, name, self)

    def __get__(self, instance, cls=None):
        """
        Accessor wrapper for a MultiColumnField, to allow for on-the-fly
        SpliceFieldInstance generation when used outside of the class.
        """
        if instance is None:
            return self
        # TODO: Add caching here
        return self.splice_attribute(instance, self)

    def __set__(self, instance, value):
        """sets all values in a MultiColumnField at once"""
        if isinstance(value, self.splice_attribute):
            # TODO: Use added cache here
            temp_field_instance = self.splice_attribute(instance, self)
            for name in self.names:
                setattr(temp_field_instance, name, getattr(value, name, None))
        elif isinstance(value, dict):
            temp_field_instance = self.splice_attribute(instance, self)
            for name in self.names:
                setattr(temp_field_instance, name, value[name])
        else:
            raise TypeError

    def instance_repr(self, instance):
        """
        A stock implementation of the __repr__ function for a generated instance of
        a MultiColumnField-derived class. The generated instance class uses the
        parent class' __instance_repr__ function to allow for easy overriding.
        """
        return "<'%s' field (MultiColumnField) on instance '%s'>" % (self.name, instance.instance.__repr__())


def splicify_field(field):
    """
    Make any field, existing or customized, splice-aware.
    In a model, field declaration will be from:
    > name = field()
    to:
    > name = splicify_field(field())()
    """
    class SpliceField(MultiColumnField):
        fields = {
            "data": field,
            "trusted": models.BooleanField(default=True),
            "synthesized": models.BooleanField(default=False),
        }
    return SpliceField
