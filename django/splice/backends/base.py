"""Base data structure class."""


class BaseStruct(object):
    def __init__(self, struct):
        """Initialize with a concrete data structure 'struct'."""
        self.struct = struct

    def save(self, data):
        """
        Public interface to insert a value, a tuple (i.e., a key
        /value pair), a list of values, or a list of tuples (for
        multi key/value pair insertion) into the data structure.
        A data structure backend can opt to implement one or more
        of these types of insertions described above.
        """
        raise NotImplementedError('subclasses of BaseStruct must provide a save() method')

    def get(self, *args, **kwargs):
        """
        All concrete data structure backends must implement this interface
        to fetch data from the data structure. Flexible parameterization.
        """
        raise NotImplementedError('subclasses of BaseStruct must provide a get() method')

    def delete(self, *args, **kwargs):
        """
        All concrete data structure backends must implement this interface
        to remove data from the data structure. Flexible parameterization.
        """
        raise NotImplementedError('subclasses of BaseStruct must provide a delete() method')

    def synthesize(self, *args, **kwargs):
        """
        All concrete data structure backends must implement this interface
        to synthesis a value or key-value pair in the data structure.
        """
        raise NotImplementedError('subclasses of BaseStruct must provide a synthesize() method')

    def __str__(self):
        """Use __str__ of the data structure itself (if defined)."""
        return self.struct.__str__()
