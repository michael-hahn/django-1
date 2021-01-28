"""Binary search tree backend"""

from django.splice.structures.bst import SynthesizableBST
from django.splice.backends.base import BaseStruct


class BaseBST(BaseStruct):
    def __init__(self):
        """Create a new data structure instance."""
        struct = SynthesizableBST()
        super().__init__(struct)

    def save(self, data):
        """data can either be a single value, a (key, value) tuple,
        a list of values or a list of (key, value) tuples. If it is
        a list (or values or tuples), insertion order follows list
        order. For a single insertion, return False if the insertion
        failed. For multi insertions, return False if at least one
        insertion failed but insertions that succeeded not be rolled
        back, so we may have a partial insertion."""
        if isinstance(data, tuple):
            return self.struct.insert(val=data[1], key=data[0])
        elif isinstance(data, list):
            success = True
            for d in data:
                if isinstance(d, tuple):
                    success &= self.struct.insert(val=d[1], key=d[0])
                else:
                    success &= self.struct.insert(val=d)
            return success
        else:
            return self.struct.insert(data)

    def get(self, key):
        return self.struct.get(key)

    def delete(self, key):
        return self.struct.delete(key)

    def synthesize(self, key):
        return self.struct.synthesize(key)


if __name__ == "__main__":
    from django.splice.structs import Struct
    from django.forms.fields import CharField, IntegerField

    class NameNumBST(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseBST()

    bst = NameNumBST(name="Jake", num=7, key="name")
    bst.save()
    bst = NameNumBST(name="Blair", num=5, key="name")
    bst.save()
    bst = NameNumBST(name="Luke", num=14, key="name")
    bst.save()
    bst = NameNumBST(name=["Andre", "Zack"], num=[9, 12], key="name")
    bst.save()
    print("Flattened key-value tree (before synthesis): {}".format(str(NameNumBST.objects)))
    print("Synthesizing root node success: {}".format(NameNumBST.objects.synthesize("Jake")))
    print("Flattened key-value tree (after synthesis): {}".format(str(NameNumBST.objects)))

    class NameOnlyBST(Struct):
        name = CharField()
        struct = BaseBST()

    bst = NameOnlyBST(name="Jake")
    bst.save()
    bst = NameOnlyBST(name="Blair")
    bst.save()
    bst = NameOnlyBST(name="Luke")
    bst.save()
    bst = NameOnlyBST(name="Andre")
    bst.save()
    bst = NameOnlyBST(name="Zack")
    bst.save()
    print("Flattened value-only tree (before synthesis): {}".format(str(NameOnlyBST.objects)))
    print("Synthesizing root node success: {}".format(NameOnlyBST.objects.synthesize("Jake")))
    print("Flattened value-only tree (after synthesis): {}".format(str(NameOnlyBST.objects)))
