"""Synthesizable sorted list data structure"""
from abc import ABC
from sortedcontainers import SortedList

from django.splice.synthesis import init_synthesizer


class SynthesizableSortedList(SortedList, ABC):
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

    def synthesis(self, index):
        """Synthesize a value at a given index in the sorted list.
        The synthesized value must ensure that the list is still sorted.
        If synthesis succeeded, return True."""
        if index >= self._len or index < 0:
            raise IndexError('list index out of range')

        value = self.__getitem__(index)
        synthesizer = init_synthesizer(value)

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


if __name__ == "__main__":
    from django.splice.untrustedtypes import UntrustedInt, UntrustedStr

    sl = SynthesizableSortedList()
    sl.update([UntrustedStr("Jake"), UntrustedStr("Blair"), UntrustedStr("Luke"),
               UntrustedStr("Andre"), UntrustedStr("Zack")])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)

    sl = SynthesizableSortedList()
    sl.update([UntrustedInt(7), UntrustedInt(5), UntrustedInt(14),
               UntrustedInt(9), UntrustedInt(12)])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)
