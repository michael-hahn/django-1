"""Sorted list backend."""

from django.splice.structures.sortedlist import SynthesizableSortedList
from django.splice.backends.base import BaseStruct


class BaseSortedList(BaseStruct):
    def __init__(self):
        """Create a new data structure backend for Sorted List."""
        super().__init__(SynthesizableSortedList())

    def save(self, data):
        if isinstance(data, list):
            for d in data:
                self.struct.add(d)
        else:
            self.struct.add(data)

    def get(self, index):
        return self.struct.__getitem__(index)

    def delete(self, value):
        return self.struct.discard(value)

    def synthesize(self, index):
        return self.struct.synthesize(index)


if __name__ == "__main__":
    from django.splice.structs import Struct
    from django.forms.fields import CharField, IntegerField

    class NameSortedList(Struct):
        """A sorted list of names (characters)."""
        name = CharField()
        struct = BaseSortedList()

    nsl = NameSortedList(name="Jake")
    nsl.save()
    nsl = NameSortedList(name="Blair")
    nsl.save()
    nsl = NameSortedList(name=["Luke", "Andre", "Zack"])
    nsl.save()
    print("NameSortedList: {}".format(NameSortedList.objects))
    NameSortedList.objects.synthesize(2)
    print("NameSortedList (after synthesizing Jake): {}".format(NameSortedList.objects))
    NameSortedList.objects.synthesize(0)
    print("NameSortedList (after synthesizing Andre): {}".format(NameSortedList.objects))
    NameSortedList.objects.synthesize(4)
    print("NameSortedList (after synthesizing Zack): {}".format(NameSortedList.objects))
    print("nsl[1] = {value}".format(value=NameSortedList.objects.get(1)))
    try:
        print("nsl[2] = {value}".format(value=NameSortedList.objects.get(2)))
    except RuntimeError as e:
        print("nsl[2] is synthesized. One should not try to get its value.")


    class NumberSortedList(Struct):
        """A sorted list of numbers (integers)."""
        num = IntegerField()
        struct = BaseSortedList()

    nsl = NumberSortedList(num=7)
    nsl.save()
    nsl = NumberSortedList(num=5)
    nsl.save()
    nsl = NumberSortedList(num=[14, 9, 12])
    nsl.save()
    print("NumberSortedList: {}".format(NumberSortedList.objects))
    NumberSortedList.objects.synthesize(2)
    print("NumberSortedList (after synthesizing 9): {}".format(NumberSortedList.objects))
    NumberSortedList.objects.synthesize(0)
    print("NumberSortedList (after synthesizing 5): {}".format(NumberSortedList.objects))
    NumberSortedList.objects.synthesize(4)
    print("NumberSortedList (after synthesizing 14): {}".format(NumberSortedList.objects))
    print("nsl[3] = {value}".format(value=NumberSortedList.objects.get(3)))
    print("nsl[4] = {value}".format(value=NumberSortedList.objects.get(4)))
    NumberSortedList.objects.delete(6)
    print("NumberSortedList (after deleting 6): {}".format(NumberSortedList.objects))
    nsl = NumberSortedList(num=[45, 0, 13])
    nsl.save()
    print("NumberSortedList (after updating with 45, 0, 13): {}".format(NumberSortedList.objects))
    for i in range(len(NumberSortedList.objects)):
        print("* nsl[{i}] = {value} "
              "(Synthesized: {synthesized})".format(i=i,
                                                    value=NumberSortedList.objects.get(i),
                                                    synthesized=NumberSortedList.objects.get(i).synthesized))
