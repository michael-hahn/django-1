"""In-memory data structure interface."""
from abc import ABCMeta
from functools import wraps
import copy

from django.forms.forms import DeclarativeFieldsMetaclass
from django.splice.backends.base import BaseStruct
from django.splice.splice import is_synthesized


def trusted_struct(cls):
    """
    Decorates a class to enforce a trusted data structure.
    One can apply this decorator on any data structure so
    that it accepts only trusted data. For example:

    @trusted_struct
    class TrustedBST(Struct):
        key = forms.CharField()
        value = forms.IntegerField()
        struct = BaseBST()
    """
    def save_wrapper(save_func):
        """Function decorator that checks the input argument of save() in all BaseStruct's subclasses."""
        @wraps(save_func)
        def wrapper(data):
            """
            Convert only non-synthesized, untrusted data to trusted data and call save().
            save() interface allows insertion of a value, a key/value pair, a list of values,
            or a list of key/value pairs into the data structure.
            """
            # TODO: insertion fails even if one of the given list of values or key/value pairs
            #  contains synthesized value. We can instead insert non-synthesized values/pairs.
            if not is_synthesized(data):
                # TODO: consider converting to trusted values? This means Base data structures
                #  should not construct Synthesizable data structures but regular ones!
                pass
                # if isinstance(data, tuple):
                #     data_0, data_1 = data[0], data[1]
                #     if isinstance(data[0], UntrustedMixin):
                #         data_0 = data[0].to_trusted()
                #     if isinstance(data[1], UntrustedMixin):
                #         data_1 = data[1].to_trusted()
                #     data = (data_0, data_1)
                # elif isinstance(data, list):
                #     for i, d in enumerate(data):
                #         if isinstance(d, tuple):
                #             data_0, data_1 = data[0], data[1]
                #             if isinstance(data[0], UntrustedMixin):
                #                 data_0 = data[0].to_trusted()
                #             if isinstance(data[1], UntrustedMixin):
                #                 data_1 = data[1].to_trusted()
                #             data[i] = (data_0, data_1)
                #         else:
                #             if isinstance(d, UntrustedMixin):
                #                 data[i] = d.to_trusted()
                # else:
                #     if isinstance(data, UntrustedMixin):
                #         data = data.to_trusted()
            else:
                raise ValueError("{data} is (a) synthesized value(s) and therefore cannot "
                                 "be inserted into a trusted data structure".format(data=data))
            return save_func(data)
        return wrapper
    for key in cls.__dict__:
        value = getattr(cls, key)
        if isinstance(value, BaseStruct):
            save = getattr(value, "save", None)
            if save:
                setattr(value, "save", save_wrapper(save))
            else:
                raise AttributeError("{cls} is a subclass of BaseStruct, but it does not have "
                                     "a required save() method defined.".format(cls=cls.__name__))
    return cls


class DeclarativeStructMetaclass(DeclarativeFieldsMetaclass):
    """
    Collect the data structure *and* its fields declared in the subclass.
    Fields are the types of data stores in the data structure. Field
    declaration is inherited directly from DeclarativeFieldsMetaclass.
    """
    def __new__(mcs, name, bases, attrs):
        # There should be only one struct field because each class
        # should be associated with at most one data structure
        struct = None
        for key, value in list(attrs.items()):
            if isinstance(value, BaseStruct):
                struct = value
                # The structure's declared name is no longer accessible.
                attrs.pop(key)
        attrs['declared_struct'] = struct

        new_class = super().__new__(mcs, name, bases, attrs)
        return new_class

    @property
    def objects(cls):
        """
        We mimic Django Model's way to retrieve data. In this case,
        data *is* the data structure itself. This 'class property'
        allows the subclass to directly access the data structure
        through dot attribute access: Subclass.objects
        """
        return cls.declared_struct


# Compose both ABCMeta and DeclarativeFieldsMetaclass. Reference:
# https://stackoverflow.com/questions/31379485/1-class-inherits-2-different-metaclasses-abcmeta-and-user-defined-meta
DeclarativeFieldsMetaWithABCMixin = type('DeclarativeFieldsMetaWithABCMixin',
                                         (ABCMeta, DeclarativeStructMetaclass), {})


class Struct(metaclass=DeclarativeStructMetaclass):
    """
    Django application developers should always inherit from this class
    if they want to use Model-like synthesizable data structures for data
    storage. To store data, developers should instantiate their subclass,
    provide in kwargs all declared fields in the subclass, and call save().

    A data structure can take values only or key/value pairs. For key/value
    pairs, the key should be one of the fields and the other field that is
    not the key is then value. The key parameter tells us which field is
    considered to be the key. kwargs can take a single value (or a key/value
    pair) or a list of values (or a list of key/value pairs).
    """
    def __init__(self, *, key=None, **kwargs):
        self.key_name = key
        # A data structure is *required*
        self.struct = self.declared_struct
        if self.struct is None:
            raise RuntimeError("you construct a data structure class without a data structure")

        self.fields = copy.deepcopy(self.base_fields)
        # Either a field for keys and a field for values, or just one field for values
        assert(len(self.fields) == 1 or len(self.fields) == 2), "you must provide either one or two fields, not" \
                                                                " {}".format(len(self.fields))

        # Make sure an object instance supplies all fields declared.
        # If key is given, make sure 'key' exists as a field name.
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
        """
        Raise a ValidationError for any errors that occur. We start with field
        cleaning and then perform struct-wide cleaning, just like how a form is
        cleaned. Calling full_clean() is optional (like in Models). But if one
        were to call full_clean(), this should probably be called before save()
        or any method that modifies the data structure, self.struct.

        IMPORTANT NOTE: Unlike in forms, clean_<name> should be aware that
        self.cleaned_data[<name>] might be a list of values instead of just a
        single value; one should always check the type with isinstance().
        """
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
        """
        Hook for doing any extra struct-wide cleaning after
        each field has been cleaned individually. clean() must
        return self.cleaned_data but perhaps with modification.
        This method can raise ValidationError.
        """
        return self.cleaned_data

    def save(self):
        """
        Public interface to insert a value, a key/value pair,
        a list of values, or a list of key/value pairs into the
        data structure. This method mimics Model.save().
        """
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
