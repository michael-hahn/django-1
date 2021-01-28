"""IntSet backend"""

from django.splice.structures.intset import SynthesizableIntSet
from django.splice.backends.base import BaseStruct


class BaseIntSet(BaseStruct):
    def __init__(self):
        """Create a new data structure instance."""
        struct = SynthesizableIntSet()
        super().__init__(struct)

    def save(self, data):
        if isinstance(data, list):
            for d in data:
                self.struct.add(value=d)
        else:
            self.struct.add(value=data)

    def get(self, pos):
        return self.struct.__getitem__(pos, self.struct._encoding)

    def delete(self, value):
        return self.struct.delete(value)

    def synthesize(self, pos):
        return self.struct.synthesize(pos)


if __name__ == "__main__":
    from django.splice.structs import Struct
    from django.forms.fields import IntegerField

    class NumberIntSet(Struct):
        """An InSet of numbers (integers)."""
        num = IntegerField()
        struct = BaseIntSet()

    int_set = NumberIntSet(num=5)
    int_set.save()
    int_set = NumberIntSet(num=30)
    int_set.save()
    int_set = NumberIntSet(num=[-7, 14, 5])
    int_set.save()
    # We should not have access to _contents but it is OK for testing
    print("intSet: {set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                                 bytes=len(NumberIntSet.objects.struct._contents)))
    int_set = NumberIntSet(num=35_267)
    int_set.save()
    # We expect the intSet to take more space now (int16 -> int32)
    print("intSet (after inserting 35267): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    int_set = NumberIntSet(num=2_447_483_647)
    int_set.save()
    # We expect the intSet to take even more space now (int32 -> int64)
    print("intSet (after inserting 2,447,483,647): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    int_set = NumberIntSet(num=[-335_267, -2_447_483_747])
    int_set.save()
    print("intSet (after inserting -335267 and -2,447,483,747): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    print("45 is in the set: {}".format(NumberIntSet.objects.struct.find(45)))
    print("35267 is in the set: {}".format(NumberIntSet.objects.struct.find(35267)))
    print("-335267 is in the set: {}".format(NumberIntSet.objects.struct.find(-335267)))
    # Delete does not "downgrading" encoding in Redis
    NumberIntSet.objects.delete(0)
    NumberIntSet.objects.delete(30)
    print("intSet (after deleting 0 and 30): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    NumberIntSet.objects.delete(-2_447_483_747)
    print("intSet (after deleting -2447483747): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    NumberIntSet.objects.delete(2_447_483_647)
    print("intSet (after deleting 2447483647): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    NumberIntSet.objects.synthesize(0)
    print("intSet (after synthesizing -335267): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    NumberIntSet.objects.synthesize(3)
    print("intSet (after synthesizing 14): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    NumberIntSet.objects.synthesize(4)
    print("intSet (after synthesizing 35267): "
          "{set} ({bytes} bytes)".format(set=NumberIntSet.objects.struct,
                                         bytes=len(NumberIntSet.objects.struct._contents)))
    print("Getting all elements from intSet through get():")
    for i in range(len(NumberIntSet.objects.struct)):
        value = NumberIntSet.objects.get(i)
        print("* int_set[{i}] = {value} (Synthesized: {synthesized}) ".format(i=i,
                                                                              value=value,
                                                                              synthesized=value.synthesized))
