"""Base data structure class"""


class BaseStruct(object):
    def __init__(self, struct):
        """struct is the concrete data structure"""
        self.struct = struct

    def save(self, data):
        """Public interface to insert a value, a tuple (i.e., a key
        /value pair), a list of values, or a list of tuples (for
        multi key/value pair insertion) into the data structure. A
        data structure backend can opt to implement one or more types
        of insertions described above, but it must override this func."""
        raise NotImplementedError('subclasses of BaseStruct must provide a save() method')

    def get(self, index_or_key):
        """All concrete data struct classes must implement this interface
        to fetch data from the data structure either by index or by key."""
        raise NotImplementedError('subclasses of BaseStruct must provide a get() method')

    def delete(self, index_or_key):
        """All concrete data struct classes must implement this interface
        to remove data from the data structure either by index or by key."""
        raise NotImplementedError('subclasses of BaseStruct must provide a delete() method')

    def synthesize(self, *args, **kwargs):
        """All concrete data struct classes must implement this interface
        to perform data structure value synthesis."""
        raise NotImplementedError('subclasses of BaseStruct must provide a synthesize() method')

    def __str__(self):
        """Use __str__ of the struct itself."""
        return self.struct.__str__()
