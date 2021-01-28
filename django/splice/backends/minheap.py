"""Binary search tree backend"""

from django.splice.structures.minheap import SynthesizableMinHeap
from django.splice.backends.base import BaseStruct


class BaseMinHeap(BaseStruct):
    def __init__(self):
        """Create a new data structure instance."""
        struct = SynthesizableMinHeap()
        super().__init__(struct)

    def save(self, data):
        if isinstance(data, list):
            for d in data:
                self.struct.add(data=d)
        else:
            self.struct.add(data=data)

    def get(self, key):
        """Key is not used."""
        return self.struct.get()

    def delete(self, key):
        """key is not used."""
        return self.struct.delete()

    def synthesize(self, index):
        return self.struct.synthesize(index)


if __name__ == "__main__":
    from django.splice.structs import Struct
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
    print("Initial int min heap:\n{mh}".format(mh=NumberMinHeap.objects.struct))
    print("Before synthesizing min, we can get min value: {min}".format(min=NumberMinHeap.objects.get(0)))
    NumberMinHeap.objects.synthesize(0)
    print("After synthesizing min:\n{mh}".format(mh=NumberMinHeap.objects.struct))
    print("Now if we get min value: {min}".format(min=NumberMinHeap.objects.get(0)))
    NumberMinHeap.objects.synthesize(2)
    print("After synthesizing an intermediate value:\n{mh}".format(mh=NumberMinHeap.objects.struct))

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
    print("Initial str min heap:\n{mh}".format(mh=NumberMinHeap.objects.struct))
    NumberMinHeap.objects.delete(0)
    print("After popping the min value:\n{mh}".format(mh=NumberMinHeap.objects.struct))
    NumberMinHeap.objects.synthesize(0)
    print("After synthesizing min:\n{mh}".format(mh=NumberMinHeap.objects.struct))
    NumberMinHeap.objects.synthesize(2)
    print("After synthesizing an intermediate value:\n{mh}".format(mh=NumberMinHeap.objects.struct))
