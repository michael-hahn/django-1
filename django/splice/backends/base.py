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

    def find(self, *args, **kwargs):
        """
        All concrete data structure backends can optionally implement this interface
        to check if data exists in the data structure. Flexible parameterization.
        Some data structures may simply opt to use __contains__ only.
        """
        raise NotImplementedError('this data structure does not support find() method')

    def synthesize(self, *args, **kwargs):
        """
        All concrete data structure backends must implement this interface
        to synthesis a value or key-value pair in the data structure.
        """
        raise NotImplementedError('subclasses of BaseStruct must provide a synthesize() method')

    def __str__(self):
        """Use __str__ of the data structure itself (if defined)."""
        return self.struct.__str__()

    def __iter__(self):
        """Use __iter__ of the data structure itself (if defined)."""
        return self.struct.__iter__()

    def __len__(self):
        """Use __len__ of the data structure itself (if defined)."""
        return self.struct.__len__()

    def __contains__(self, item):
        """Use __contains__ of the data structure itself (if defined)."""
        return self.struct.__contains__(item)
