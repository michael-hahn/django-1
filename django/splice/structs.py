"""In-memory data structure high-level interface"""
from abc import ABC, abstractmethod

from django.splice.untrustedtypes import synthesis_error, synthesis_warning, untrustify


class BaseSynthesizableStruct(ABC):
    """All data structures must inherit from this class, which provides
    a generic interface and incorporates synthesis-aware features."""
    def __init__(self, *args, **kwargs):
        """Cooperative multi-inheritance"""
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        """This is used to automatically decorate all subclasses having
        get() and peak() functions with synthesis_error and synthesis_warning,
        respectively and save() and synthesize() with untrustify."""
        super().__init_subclass__(**kwargs)
        get_func = getattr(cls, 'get', None)
        peek_func = getattr(cls, 'peek', None)
        save_func = getattr(cls, 'save', None)
        synthesize_func = getattr(cls, 'synthesize', None)
        if get_func:
            setattr(cls, 'get', synthesis_error(get_func))
        if peek_func:
            setattr(cls, 'peek', synthesis_warning(peek_func))
        if save_func:
            setattr(cls, 'save', untrustify(save_func))
        if synthesize_func:
            setattr(cls, 'synthesize', untrustify(synthesize_func))

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

