"""Binary search tree backend."""

from django.splice.structures.bst import SynthesizableBST
from django.splice.backends.base import BaseStruct


class BaseBST(BaseStruct):
    def __init__(self):
        """Create a new data structure backend for BST."""
        super().__init__(SynthesizableBST())

    def save(self, data):
        """
        'data' can be a (key, value) tuple, or a list of
        (key, value) tuples. If it is a list, insertion
        order follows the list order. For a single insertion,
        return False if the insertion failed. For multi insertions,
        return False if at least one insertion failed but
        insertions that succeeded prior to the failure won't be
        rolled back, so we may have a partial insertion.
        """
        if isinstance(data, tuple):
            return self.struct.insert(data[0], data[1])
        elif isinstance(data, list):
            success = True
            for d in data:
                if isinstance(d, tuple):
                    success &= self.struct.insert(d[0], d[1])
                else:
                    raise ValueError("a (key, value) tuple is expected, but got {}".format(d))
            return success
        else:
            raise ValueError("a (key, value) tuple is expected, but got {}".format(data))

    def get(self, key):
        return self.struct.get(key)

    def delete(self, key):
        return self.struct.delete(key)

    def find(self, key):
        return self.struct.find(key)

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
