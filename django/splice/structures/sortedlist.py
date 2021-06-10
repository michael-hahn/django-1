"""Synthesizable sorted list data structure"""
# from django.splice.replace import replace
from sortedcontainers import SortedList

from django.splice.splicetypes import SpliceMixin
from django.splice.synthesis import init_synthesizer
from django.splice.structs import SpliceStructMixin


class SynthesizableSortedList(SortedList):
    """Inherit from SortedList to create a custom sorted list
    that behaves exactly like a sorted list (with elements sorted
    in the list) but the elements in the SynthesizableSortedList
    can be synthesized. Reference of the sorted containers:
    http://www.grantjenks.com/docs/sortedcontainers/sortedlist.html."""
    def __setitem__(self, index, value):
        """SortedList raise not-implemented error when calling
        __setitem__ because it will not allow users to simply
        replace a value at index (in case the list becomes
        unsorted). We implement this function based on SortedList
        __getitem__ implementation for direct replacement so that
        synthesis can replace a value directly. Note that our
        synthesis guarantees the sorted order so it is OK to do
        so, but the user of SynthesizableSortedList should not
        call this function.

        This function is implemented specifically for our synthesis.
        One should not use this function to e.g., append a new value.

        Note that We are unfortunately using many supposedly
        "protected" instance attributes to implement __setitem__."""
        _lists = self._lists
        _maxes = self._maxes

        pos, idx = self._pos(index)
        _lists[pos][idx] = value
        # SortedList maintains a list of maximum values for each sublist.
        # We must update the maximum value if "value" becomes the
        # maximum value of its sublist.
        if idx == len(_lists[pos]) - 1:
            _maxes[pos] = value

    def synthesize(self, index):
        """Synthesize a value at a given index in the sorted list.
        The synthesized value must ensure that the list is still sorted.
        If synthesis succeeded, return True."""
        if index >= self._len or index < 0:
            raise IndexError('list index out of range')

        value = self.__getitem__(index)
        synthesizer = init_synthesizer(value)

        if self._len == 1:
            # If there is only one element in the sortedlist
            # We use simple_synthesis() for now
            self.__setitem__(index, synthesizer.simple_synthesis(value))
            return True

        if index == 0:
            # The value to be synthesized is the smallest in the sorted list
            synthesizer.lt_constraint(self.__getitem__(index + 1))
        elif index == self._len - 1:
            # The value to be synthesized is the largest in the sorted list
            synthesizer.gt_constraint(self.__getitem__(index - 1))
        else:
            # The value to be synthesized is in the middle of the sorted list
            synthesizer.bounded_constraints(upper_bound=self.__getitem__(index + 1),
                                            lower_bound=self.__getitem__(index - 1))
        synthesized_value = synthesizer.to_python(synthesizer.value)
        self.__setitem__(index, synthesized_value)
        return True


class SpliceSortedList(SpliceStructMixin, SortedList):
    """
    Inherit from SortedList to create a custom sorted list
    that behaves exactly like a sorted list (with elements sorted
    in the list), but 1) any insertion converts input into an
    untrusted Splice* object (so we require that inserted objects
    are Splice* objects only); 2) defines additional methods
    for constraint concretization.
    """
    def enclosing(self, obj):
        """
        Given a Splice* object 'obj', we return the index of the
        enclosing item that is inserted into SpliceSortedList.
        """
        i = self.index(obj)
        while id(obj) != id(self.__getitem__(i)):
            i = self.index(obj, start=i+1)
        return i

    def add(self, value):
        """
         Convert value into an untrusted Splice value
         and then call SortedList's add() method. Depending
         on the type of 'value' we would attach different
         symbolic constraints and their callbacks.
         """
        assert isinstance(value, SpliceMixin), "SpliceSortedList accepts only Splice* objects"
        value = self.splicify(value, concretize_cb=self.concretize_cb("gt(prev(enclosing())) AND "
                                                                      "lt(next(enclosing())) AND "
                                                                      "ne(self())"))
        super().add(value)

    # TODO: SortedList defines a number of other methods to insert
    #  data. We should instrument them like in add().

    # Methods called by synthesis constraints ===========
    def next(self, index):
        """Get the item next to the given index."""
        if index == len(self) - 1:
            return None
        else:
            return self.__getitem__(index + 1)

    def prev(self, index):
        """Get the item prior to the given index."""
        if index == 0:
            return None
        else:
            return self.__getitem__(index - 1)

    def self(self, obj):
        """Return the "obj" itself."""
        return obj


class SpliceSortedListTuple(SpliceStructMixin, SortedList):
    """
    Inherit from SortedList to create a custom sorted list
    that behaves exactly like a sorted list (with elements sorted
    in the list), but 1) input to the sorted list is a tuple of
    two Splice* objects, 2) any insertion converts objects in the
    tuple to be untrusted; 3) defines additional methods for
    constraint concretization.
    """
    def enclosing(self, obj):
        """
        Given a Splice* object 'obj', we return the index of the
        enclosing tuple that is inserted into SpliceSortedList.
        """
        for t in self.__iter__():
            if id(obj) == id(t[0]) or id(obj) == id(t[1]):
                return self.index(t)

    def add(self, value):
        """
         Convert value into an untrusted Splice value
         and then call SortedList's add() method. Depending
         on the type of 'value' we would attach different
         symbolic constraints and their callbacks.
         """
        assert isinstance(value, tuple), "SpliceSortedList accepts only tuples"
        assert isinstance(value[0], SpliceMixin)
        assert isinstance(value[1], SpliceMixin)
        first = self.splicify(value[0], concretize_cb=self.concretize_cb(
            "if ge(second(prev(enclosing())) second(get(enclosing()))) "
            "   then gt(first(prev(enclosing()))) AND ne(self())"
            "else ge(first(prev(enclosing()))) AND ne(self())"
            "if le(second(next(enclosing())) second(get(enclosing()))) "
            "   then lt(first(next(enclosing()))) AND ne(self())"
            "else le(first(next(enclosing()))) AND ne(self())"))
        second = self.splicify(value[1], concretize_cb=self.concretize_cb(
            "if eq(first(prev(enclosing())) first(get(enclosing()))) "
            "   then gt(second(prev(enclosing()))) AND ne(self())"
            "if eq(first(next(enclosing())) first(get(enclosing()))) "
            "   then lt(second(next(enclosing()))) AND ne(self())"))
        super().add((first, second))

    # TODO: SortedList defines a number of other methods to insert
    #  data. We should instrument them like in add().

    # Methods called by synthesis constraints ===========
    def next(self, index):
        """Get the item next to the given index."""
        if index == len(self) - 1:
            return False
        else:
            return self.__getitem__(index + 1)

    def prev(self, index):
        """Get the item prior to the given index."""
        if index == 0:
            return False
        else:
            return self.__getitem__(index - 1)

    def first(self, t):
        if not t:
            return False
        else:
            return t[0]

    def second(self, t):
        if not t:
            return False
        else:
            return t[1]

    def get(self, index):
        return self.__getitem__(index)

    def ge(self, a, b):
        if not a or not b:
            return False
        else:
            return a >= b

    def le(self, a, b):
        if not a or not b:
            return False
        else:
            return a <= b

    def eq(self, a, b):
        if not a or not b:
            return False
        else:
            return a == b

    def self(self, obj):
        """Return the "obj" itself."""
        return obj


if __name__ == "__main__":
    from django.splice.splicetypes import SpliceInt, SpliceStr
    from django.splice.identity import empty_taint
    from django.splice.constraints import merge_constraints
    import gc
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django.settings")

    # Set up a SpliceSortedList instance
    taint = empty_taint()
    taint[30] = True
    a = SpliceInt(12345, trusted=True, synthesized=False, taints=taint)
    b = SpliceInt(9876, trusted=True, synthesized=False, taints=taint)
    c = SpliceInt(34567, trusted=True, synthesized=False, taints=taint)
    taint2 = empty_taint()
    taint2[8] = True
    d = SpliceInt(12456, trusted=True, synthesized=False, taints=taint2)
    # l = SpliceSortedList()
    # l.add(a)
    # l.add(b)
    # l.add(c)
    # l.add(d)

    # Set up a SpliceSortedListTuple instance
    ka = SpliceStr("ABCDE", trusted=True, synthesized=False, taints=taint)
    kb = SpliceStr("FGHI", trusted=True, synthesized=False, taints=taint)
    kc = SpliceStr("JKLM", trusted=True, synthesized=False, taints=taint)
    kd = SpliceStr("NOPQR", trusted=True, synthesized=False, taints=taint2)
    l = SpliceSortedListTuple()
    l.add((a, ka))
    l.add((b, kb))
    l.add((c, kc))
    l.add((d, kd))

    # Test GC
    objs = gc.get_objects()
    for obj in objs:
        # Only Splice objects with the taint of the user to be deleted need to be synthesized.
        # Note that our (SpliceInt, SpliceStr) tuples are included in GC's get_objects() output!
        if isinstance(obj, SpliceMixin) and obj.taints == taint:
            # Perform Splice object deletion through synthesis.
            synthesizer = init_synthesizer(obj)
            # Concretize constraints for obj using symbolic constraints from its
            # enclosing data structure.
            concrete_constraints = []
            for constraint in obj.constraints:
                concrete_constraints.append(constraint(obj))
            # Merge all concrete constraints, if needed
            if not concrete_constraints:
                merged_constraints = None
            else:
                merged_constraints = concrete_constraints[0]
                for concrete_constraint in concrete_constraints[1:]:
                    merged_constraints = merge_constraints(merged_constraints, concrete_constraint)
            # Synthesis handles setting trusted and synthesized flags properly
            synthesized_obj = synthesizer.splice_synthesis(merged_constraints)
            if synthesized_obj is not None:
                replace(obj, synthesized_obj)
            else:
                # If synthesis failed for some reason, the best we can do is to change object attributes.
                obj.trusted = False
                obj.synthesized = True
                obj.taints = empty_taint()
                obj.constraints = []
    # Potential issue of Z3 after program exits: https://github.com/Z3Prover/z3/issues/989
