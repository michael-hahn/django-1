"""Synthesizable sorted list data structure"""
from sortedcontainers import SortedList

from django.splice.synthesis import init_synthesizer
from django.splice.structs import BaseSynthesizableStruct


class SynthesizableSortedList(SortedList, BaseSynthesizableStruct):
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

    def save(self, value):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        store data into SynthesizableSortedList."""
        self.add(value)

    def get(self, key):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        obtain data from SynthesizableSortedList."""
        return self.__getitem__(key)


if __name__ == "__main__":
    sl = SynthesizableSortedList()
    sl.save("Jake")
    sl.save("Blair")
    sl.save("Luke")
    sl.save("Andre")
    sl.save("Zack")
    print("SortedList: {}".format(sl))
    sl.synthesize(2)
    print("SortedList (after synthesizing Jake): {}".format(sl))
    sl.synthesize(0)
    print("SortedList (after synthesizing Andre): {}".format(sl))
    sl.synthesize(4)
    print("SortedList (after synthesizing Zack): {}".format(sl))
    print("sl[1] = {value}".format(value=sl.get(1)))
    try:
        print("sl[2] = {value}".format(value=sl.get(2)))
    except RuntimeError as e:
        print("sl[2] is synthesized. One should not try to get its value.")

    sl = SynthesizableSortedList()
    sl.save(7)
    sl.save(5)
    sl.save(14)
    sl.save(9)
    sl.save(12)
    print("SortedList: {}".format(sl))
    sl.synthesize(2)
    print("SortedList (after synthesizing 9): {}".format(sl))
    sl.synthesize(0)
    print("SortedList (after synthesizing 5): {}".format(sl))
    sl.synthesize(4)
    print("SortedList (after synthesizing 14): {}".format(sl))
    print("sl[3] = {value}".format(value=sl.get(3)))
    try:
        print("sl[4] = {value}".format(value=sl.get(4)))
    except RuntimeError as e:
        print("sl[4] is synthesized. One should not try to get its value.")
