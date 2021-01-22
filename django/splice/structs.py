"""In-memory data structure high-level interface"""
from abc import ABC, abstractmethod

from django.splice.untrustedtypes import untrustify


class BaseSynthesizableStruct(ABC):
    """All data structures must inherit from this class, which provides
    a generic interface and incorporates synthesis-aware features."""
    def __init__(self, *args, **kwargs):
        """Cooperative multi-inheritance"""
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        """This is used to automatically decorate all subclasses
         function with untrustify."""
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
    def save(self, **kwargs):
        """All concrete data struct classes must implement this
        interface to insert/store data into the data structure."""
        pass

    @abstractmethod
    def get(self, **kwargs):
        """All concrete data struct classes must implement this
        interface to query the data structure. Query will fail
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


if __name__ == "__main__":
    pass

