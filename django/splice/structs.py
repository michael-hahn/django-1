"""In-memory data structure high-level interface"""
from abc import ABCMeta, abstractmethod
import copy

from django.forms.forms import DeclarativeFieldsMetaclass
from django.splice.untrustedtypes import untrustify


# Compose both ABCMeta and DeclarativeFieldsMetaclass
# Reference:
# https://stackoverflow.com/questions/31379485/1-class-inherits-2-different-metaclasses-abcmeta-and-user-defined-meta
DeclarativeFieldsMetaWithABCMixin = type('DeclarativeFieldsMetaWithABCMixin',
                                         (ABCMeta, DeclarativeFieldsMetaclass), {})


class BaseSynthesizableStruct(metaclass=DeclarativeFieldsMetaWithABCMixin):
    """All data structures must inherit from this class, which provides
    a generic interface and incorporates synthesis-aware features. This
    class should probably always be the first inherited superclass!"""
    def __init__(self, *args, **kwargs):
        """Cooperative multi-inheritance"""
        super().__init__(*args, **kwargs)
        self.fields = copy.deepcopy(self.base_fields)

    def __init_subclass__(cls, **kwargs):
        """This is used to automatically decorate all subclasses
         function with untrustify.

         TODO: This method may no longer be needed with the new save() implementation!
         """
        super().__init_subclass__(**kwargs)
        decorated_funcs = set()
        # We can interested in decorating callable, non-dunder functions
        # It is unlikely that data structures uses dunder methods except
        # maybe __getitem__, __setitem__, and __delitem__.
        for c in cls.__mro__:
            for key, value in c.__dict__.items():
                if not callable(value) or key.startswith("__") or key in decorated_funcs:
                    continue
                setattr(c, key, untrustify(value))
                decorated_funcs.add(key)
        # Special cases not handled above
        get_dunder = getattr(cls, "__getitem__", None)
        set_dunder = getattr(cls, "__setitem__", None)
        del_dunder = getattr(cls, "__delitem__", None)
        if get_dunder:
            setattr(cls, "__getitem__", untrustify(get_dunder))
        if set_dunder:
            setattr(cls, "__setitem__", untrustify(set_dunder))
        if del_dunder:
            setattr(cls, "__delitem__", untrustify(del_dunder))
        #############################################
        # TODO: Add more special cases here if needed
        #############################################

    @abstractmethod
    def __save__(self, cleaned_data):
        """All concrete data struct classes must implement this
        helper function to insert/store data into the data structure.
        It takes a dictionary of data to be inserted into the
        data structure. 'cleaned_data' is already cleaned by save()."""
        pass

    def save(self, **kwargs):
        """Public interface to insert a value or a key/value pair
        into the data structure. Each data structure inherited from
        this class determines name conventions used in fields. Note
        that field names will be the keys of 'cleaned_data' passed
        to __save__, which must be implemented by the subclass!"""
        cleaned_data = {}
        for name, field in self.fields.items():
            # User must provide all values indicated in the field declaration
            if name not in kwargs:
                raise ValueError("{name} is required by the data structure.".format(name=name))
            # Iteration stops if any field does not pass validation
            value = kwargs[name]
            value = field.clean(value)
            cleaned_data[name] = value
            if hasattr(self, 'clean_%s' % name):
                value = getattr(self, 'clean_%s' % name)()
                cleaned_data[name] = value
        # Struct-wide clean
        cleaned_data = BaseSynthesizableStruct.clean(cleaned_data)
        # Last check to make sure at least something is in the cleaned_data.
        # Otherwise there is no point calling __save__ to add empty values.
        # If nothing is passed to __save__, then do nothing.
        if not cleaned_data:
            return
        # Finally, add to data structure
        self.__save__(cleaned_data)

    @abstractmethod
    def get(self, **kwargs):
        """All concrete data struct classes must implement this
        interface to query the data structure. Query should fail
        if data queried from the data structure is synthesized."""
        pass

    @abstractmethod
    def delete(self, **kwargs):
        """All concrete data struct classes must implement this
        interface to remove the data from the data structure."""
        pass

    def peek(self, *args, **kwargs):
        """Concrete data struct classes can optionally implement
        this interface to query the data structure. Query will output
        warnings if data queried is synthesized, but it will not fail."""
        raise NotImplementedError("peek() is not implemented by the data structure")

    @abstractmethod
    def synthesize(self, *args, **kwargs):
        """All concrete data struct classes must implement this
        interface to perform data structure value synthesis."""
        pass

    @staticmethod
    def clean(cleaned_data):
        """Hook for doing any extra struct-wide cleaning after
        Field.clean() has been called on every field. clean()
        must take a dictionary of previously clean data and
        return the same dictionary but perhaps with modification."""
        return cleaned_data


if __name__ == "__main__":
    pass
