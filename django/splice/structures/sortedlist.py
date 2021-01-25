"""Synthesizable sorted list data structure"""
from sortedcontainers import SortedList

from django.splice.synthesis import init_synthesizer
from django.splice.structs import BaseSynthesizableStruct


class SynthesizableSortedList(BaseSynthesizableStruct, SortedList):
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

    def __save__(self, cleaned_data):
        """BaseSynthesizableStruct enforces implementation of this method. A
        subclass of this class can also override this method for a customized store.

        The default behavior is that cleaned_data contains only one element
        and this element is to be inserted into the sorted list."""
        if len(cleaned_data) > 1:
            raise ValueError("By default, only one value can be inserted "
                             "at a time using save(). You may want to override"
                             "__save__() for customized insertion.")
        for key, value in cleaned_data.items():
            self.add(value)

    def get(self, idx):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        obtain data from SynthesizableSortedList."""
        return self.__getitem__(idx)

    def delete(self, value):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        obtain data from SynthesizableSortedList."""
        return self.discard(value)


if __name__ == "__main__":
    from django.forms.fields import CharField, IntegerField

    class NameSortedList(SynthesizableSortedList):
        """A sorted list of names (characters)."""
        name = CharField()

    nsl = NameSortedList()
    nsl.save(name="Jake")
    nsl.save(name="Blair")
    nsl.save(name="Luke")
    nsl.save(name="Andre")
    nsl.save(name="Zack")
    print("NameSortedList: {}".format(nsl))
    nsl.synthesize(2)
    print("NameSortedList (after synthesizing Jake): {}".format(nsl))
    nsl.synthesize(0)
    print("NameSortedList (after synthesizing Andre): {}".format(nsl))
    nsl.synthesize(4)
    print("NameSortedList (after synthesizing Zack): {}".format(nsl))
    print("nsl[1] = {value}".format(value=nsl.get(1)))
    try:
        print("nsl[2] = {value}".format(value=nsl.get(2)))
    except RuntimeError as e:
        print("nsl[2] is synthesized. One should not try to get its value.")


    class NumberSortedList(SynthesizableSortedList):
        """A sorted list of numbers (integers)."""
        num = IntegerField()

    nsl = NumberSortedList()
    nsl.save(num=7)
    nsl.save(num=5)
    nsl.save(num=14)
    nsl.save(num=9)
    nsl.save(num=12)
    print("NumberSortedList: {}".format(nsl))
    nsl.synthesize(2)
    print("NumberSortedList (after synthesizing 9): {}".format(nsl))
    nsl.synthesize(0)
    print("NumberSortedList (after synthesizing 5): {}".format(nsl))
    nsl.synthesize(4)
    print("NumberSortedList (after synthesizing 14): {}".format(nsl))
    print("nsl[3] = {value}".format(value=nsl.get(3)))
    print("nsl[4] = {value}".format(value=nsl.get(4)))
    nsl.delete(6)
    print("NumberSortedList (after deleting 6): {}".format(nsl))
    nsl.update([45, 0, 13])
    print("NumberSortedList (after updating with 45, 0, 13): {}".format(nsl))
    for i in range(len(nsl)):
        print("* nsl[{i}] = {value} (Synthesized: {synthesized})".format(i=i, value=nsl.get(i),
                                                                         synthesized=nsl.get(i).synthesized))
