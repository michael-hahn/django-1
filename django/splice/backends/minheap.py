"""MinHeap backend."""

from django.splice.structures.minheap import SynthesizableMinHeap
from django.splice.backends.base import BaseStruct


class BaseMinHeap(BaseStruct):
    def __init__(self):
        """Create a new data structure backend for MinHeap."""
        super().__init__(SynthesizableMinHeap())

    def save(self, data):
        if isinstance(data, list):
            for d in data:
                self.struct.add(data=d)
        else:
            self.struct.add(data=data)

    def get(self):
        return self.struct.get()

    def delete(self):
        return self.struct.pop()

    def synthesize(self, index):
        return self.struct.synthesize(index)

    def __iter__(self):
        return self.struct.__iter__()


if __name__ == "__main__":
    from django.splice.structs import Struct, trusted_struct
    from django.forms.fields import CharField, IntegerField

    class NumberMinHeap(Struct):
        """A min heap of numbers (integers)."""
        num = IntegerField()
        struct = BaseMinHeap()

    mh = NumberMinHeap(num=4)
    mh.save()
    mh = NumberMinHeap(num=3)
    mh.save()
    mh = NumberMinHeap(num=[5, 12, 5, 7, 1])
    mh.save()
    print("Initial int min heap:\n{mh}".format(mh=NumberMinHeap.objects))
    print("Before synthesizing min, we can get min value: {min}".format(min=NumberMinHeap.objects.get()))
    NumberMinHeap.objects.synthesize(0)
    print("After synthesizing min:\n{mh}".format(mh=NumberMinHeap.objects))
    print("Now if we get min value: {min}".format(min=NumberMinHeap.objects.get()))
    NumberMinHeap.objects.synthesize(2)
    print("After synthesizing an intermediate value:\n{mh}".format(mh=NumberMinHeap.objects))

    class NameMinHeap(Struct):
        """A min heap of names (characters)."""
        name = CharField()
        struct = BaseMinHeap()

    mh = NameMinHeap(name="Jake")
    mh.save()
    mh = NameMinHeap(name="Blair")
    mh.save()
    mh = NameMinHeap(name=["Luke", "Andre", "Zack", "Tommy", "Sandra"])
    mh.save()
    print("Initial str min heap:\n{mh}".format(mh=NameMinHeap.objects))
    NameMinHeap.objects.delete()
    print("After popping the min value:\n{mh}".format(mh=NameMinHeap.objects))
    NameMinHeap.objects.synthesize(0)
    print("After synthesizing min:\n{mh}".format(mh=NameMinHeap.objects))
    NameMinHeap.objects.synthesize(2)
    print("After synthesizing an intermediate value:")
    for n in NameMinHeap.objects:
        print("* {} (synthesized: {})".format(n, n.synthesized))

    @trusted_struct
    class TrustedNameMinHeap(Struct):
        """A min heap of trusted names only."""
        name = CharField()
        struct = BaseMinHeap()

    for n in NameMinHeap.objects:
        tmh = TrustedNameMinHeap(name=n)
        try:
            tmh.save()
        except ValueError as e:
            print("Cannot save {}, because {}".format(n, e))
    print("Enumerate all elements in TrustedNameMinHeap:")
    for n in TrustedNameMinHeap.objects:
        print("* {}".format(n))
