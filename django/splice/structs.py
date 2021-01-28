"""In-memory data structure high-level interface"""
from abc import ABCMeta
import copy

from django.forms.forms import DeclarativeFieldsMetaclass
from django.splice.backends.base import BaseStruct


class DeclarativeStructMetaclass(DeclarativeFieldsMetaclass):
    """Collect the data structure declared on the subclass."""
    def __new__(mcs, name, bases, attrs):
        # There should be only one struct field because each class
        # should be associated with at most one data structure
        struct = None
        for key, value in list(attrs.items()):
            if isinstance(value, BaseStruct):
                struct = value
                attrs.pop(key)
        attrs['declared_struct'] = struct

        new_class = super().__new__(mcs, name, bases, attrs)
        return new_class

    @property
    def objects(cls):
        """This is to mimic Django model's way to retrieve objects."""
        return cls.declared_struct


# Compose both ABCMeta and DeclarativeFieldsMetaclass
# Reference:
# https://stackoverflow.com/questions/31379485/1-class-inherits-2-different-metaclasses-abcmeta-and-user-defined-meta
DeclarativeFieldsMetaWithABCMixin = type('DeclarativeFieldsMetaWithABCMixin',
                                         (ABCMeta, DeclarativeStructMetaclass), {})


class Struct(metaclass=DeclarativeStructMetaclass):
    """All data structures must inherit from this class, which provides
    a generic interface and incorporates synthesis-aware features. This
    class should probably always be the first inherited superclass!

    For initialization, all fields declared in the subclass must exist
    in kwargs. If a data structure takes both a key and a value, the key
    should be one of the fields. The field that is not key is the value.
    kwargs can take a single value or a list of values."""
    def __init__(self, *, key=None, **kwargs):
        self.key_name = key
        # A data structure is required
        self.struct = self.declared_struct
        if self.struct is None:
            raise RuntimeError("you construct a data structure class without a data structure")

        self.fields = copy.deepcopy(self.base_fields)
        # Either a field for key and a field for value or just one field
        assert(len(self.fields) == 1 or len(self.fields) == 2), "you must provide either one or two fields, not" \
                                                                " {}".format(len(self.fields))

        # Make sure an object instance supplies all fields declared.
        # If key is given, make sure 'key' exist as a field name.
        self.cleaned_data = {}
        if key and key not in self.fields:
            raise RuntimeError("key '{}' must be a declared field".format(key))
        for name, field in self.fields.items():
            if name != key:
                self.value_name = name
            if name not in kwargs:
                raise RuntimeError("missing a value for the '{}' field".format(name))
            else:
                # values are converted into untrusted values and then put into self.cleaned_data
                if isinstance(kwargs[name], list):
                    self.cleaned_data[name] = [field.to_python(v) for v in kwargs[name]]
                else:
                    self.cleaned_data[name] = field.to_python(kwargs[name])
        # Last check to make sure each value in self.cleaned_data
        # has the same length if it is a list (not a single value)
        if key:
            if isinstance(self.cleaned_data[self.key_name], list):
                assert(isinstance(self.cleaned_data[self.value_name], list) and
                       len(self.cleaned_data[self.key_name])
                       == len(self.cleaned_data[self.value_name])), "must provide the same number of keys and values"
            else:
                assert(not isinstance(self.cleaned_data[self.value_name], list)), "a single key cannot " \
                                                                                  "have a list of values"

    def full_clean(self):
        """Raise a ValidationError for any errors that occur. We start with field
        cleaning and then struct-wide cleaning just like how form is cleaned. Calling
        full_clean() is optional (like in Models). But if one were to call full_clean(),
        this should probably be called before save() or any method that modify self.struct.

        IMPORTANT NOTE: Unlike in forms, clean_name should be aware that self.cleaned_data[name]
        might be a list of values instead of just a single value; always check with isinstance()!"""
        for name, field in self.fields.items():
            # Iteration stops if any field does not pass validation
            # We checked in __init__ that name must exist in self.data
            if isinstance(self.cleaned_data[name], list):
                for value in self.cleaned_data[name]:
                    field.validate(value)
                    field.run_validators(value)
            else:
                field.validate(self.cleaned_data[name])
                field.run_validators(self.cleaned_data[name])
            if hasattr(self, 'clean_%s' % name):
                self.cleaned_data[name] = getattr(self, 'clean_%s' % name)()
        # struct-wide clean
        self.cleaned_data = self.clean()

    def clean(self):
        """Hook for doing any extra struct-wide cleaning after
        each field has been cleaned individually. clean() must
        return self.cleaned_data but perhaps with modification.
        clean() can raise ValidationError."""
        return self.cleaned_data

    def save(self):
        """Public interface to insert a value, a key/value pair, a list of
        values or a list of key/value pairs into the data structure."""
        if self.key_name:
            if isinstance(self.cleaned_data[self.key_name], list):
                data = list(zip(self.cleaned_data[self.key_name], self.cleaned_data[self.value_name]))
            else:
                data = (self.cleaned_data[self.key_name], self.cleaned_data[self.value_name])
        else:
            data = self.cleaned_data[self.value_name]
        self.struct.save(data)


if __name__ == "__main__":
    pass
