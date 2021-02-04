"""Hash Table backend."""

from django.splice.structures.hashtable import SynthesizableHashTable, SynthesizableDict
from django.splice.backends.base import BaseStruct
from django.splice.untrustedtypes import UntrustedMixin, to_untrusted


class BaseHashTable(BaseStruct):
    def __init__(self):
        """Create a new data structure backend for hash table."""
        super().__init__(SynthesizableHashTable())

    def save(self, data):
        """'data' can be a (key, value) tuple, or a list of (key, value) tuples."""
        if isinstance(data, tuple):
            self.struct.__setitem__(key=data[0], value=data[1])
        elif isinstance(data, list):
            for d in data:
                if isinstance(d, tuple):
                    self.struct.__setitem__(key=d[0], value=d[1])
                else:
                    raise ValueError("a (key, value) tuple is expected, but got {}".format(d))
        else:
            raise ValueError("a (key, value) tuple is expected, but got {}".format(data))

    # TODO: hash is used to identify items, but since we modified __hash__ for
    #  UntrustedStr, a str can have the same value as an UntrustedStr but they
    #  will have different hash values. We use a hack here to change a str key
    #  to an UntrustedStr key, but __hash__ is ultimate proper fix (BaseDict too)
    def get(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        return self.struct.__getitem__(key)

    def delete(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        return self.struct.__delitem__(key)

    def synthesize(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        return self.struct.synthesize(key)

    def __iter__(self):
        return self.struct.__iter__()


class BaseDict(BaseStruct):
    def __init__(self):
        """Create a new data structure backend for dict."""
        super().__init__(SynthesizableDict())

    def save(self, data):
        """'data' can be a (key, value) tuple, or a list of (key, value) tuples."""
        if isinstance(data, tuple):
            self.struct[data[0]] = data[1]
        elif isinstance(data, list):
            for d in data:
                if isinstance(d, tuple):
                    self.struct[d[0]] = d[1]
                else:
                    raise ValueError("a (key, value) tuple is expected, but got {}".format(d))
        else:
            raise ValueError("a (key, value) tuple is expected, but got {}".format(data))

    def get(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        return self.struct[key]

    def delete(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        del self.struct[key]

    def synthesize(self, key):
        if not isinstance(key, UntrustedMixin):
            key = to_untrusted(key, synthesized=False)
        return self.struct.synthesize(key)

    def __iter__(self):
        return self.struct.__iter__()


if __name__ == "__main__":
    from django.splice.structs import Struct, trusted_struct
    from django.forms.fields import CharField, IntegerField

    class NameNumHashTable(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseHashTable()

    ht = NameNumHashTable(name="Jake", num=7, key="name")
    ht.save()
    ht = NameNumHashTable(name="Blair", num=5, key="name")
    ht.save()
    ht = NameNumHashTable(name=["Luke", "Andre", "Zack"], num=[14, 9, 12], key="name")
    ht.save()
    print("Enumerating a string-keyed hash table:")
    for key in NameNumHashTable.objects:
        value = NameNumHashTable.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))
    NameNumHashTable.objects.synthesize("Blair")
    print("After deleting 'Blair' by synthesis, enumerate again:")
    for key in NameNumHashTable.objects:
        value = NameNumHashTable.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))

    @trusted_struct
    class TrustedNameNumHashTable(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseHashTable()

    for key in NameNumHashTable.objects:
        value = NameNumHashTable.objects.get(key)
        tht = TrustedNameNumHashTable(name=key, num=value, key="name")
        try:
            tht.save()
        except ValueError as e:
            print("Cannot save ({}, {}), because {}".format(key, value, e))
    print("Enumerating a trusted string-keyed hash table:")
    for key in TrustedNameNumHashTable.objects:
        value = TrustedNameNumHashTable.objects.get(key)
        print("* {key} (hash: {hash})"
              " -> {value}".format(key=key, hash=key.__hash__(), value=value))

    class NumNameHashTable(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseHashTable()

    ht = NumNameHashTable(name="Jake", num=7, key="num")
    ht.save()
    # We need a super big integer key so that the synthesized integer
    # value would be different from this original value
    ht = NumNameHashTable(name="Blair", num=32_345_435_432_758_439_203_535_345_435, key="num")
    ht.save()
    ht = NumNameHashTable(name=["Luke", "Andre", "Zack"], num=[14, 9, 12], key="num")
    ht.save()
    print("Enumerating an int-keyed hash table:")
    for key in NumNameHashTable.objects:
        value = NumNameHashTable.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))
    NumNameHashTable.objects.synthesize(32_345_435_432_758_439_203_535_345_435)
    print("After deleting '32345435432758439203535345435' by synthesis, enumerate again:")
    for key in NumNameHashTable.objects:
        value = NumNameHashTable.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))

    class NameNumDict(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseDict()

    ht = NameNumDict(name="Jake", num=7, key="name")
    ht.save()
    ht = NameNumDict(name="Blair", num=5, key="name")
    ht.save()
    ht = NameNumDict(name=["Luke", "Andre", "Zack"], num=[14, 9, 12], key="name")
    ht.save()
    print("Enumerating a string-keyed hash table:")
    for key in NameNumDict.objects:
        value = NameNumDict.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))
    NameNumDict.objects.synthesize("Luke")
    print("After deleting 'Luke' by synthesis, enumerate again:")
    for key in NameNumDict.objects:
        value = NameNumDict.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))
    NameNumDict.objects.delete("Andre")
    print("After deleting 'Andre' by calling delete(), enumerate again:")
    for key in NameNumDict.objects:
        value = NameNumDict.objects.get(key)
        print("* {key} (hash: {hash}, Synthesized: {synthesis_key})"
              " -> {value} [Synthesized: {synthesis_value}]".format(key=key,
                                                                    hash=key.__hash__(),
                                                                    synthesis_key=key.synthesized,
                                                                    value=value,
                                                                    synthesis_value=value.synthesized))

    @trusted_struct
    class TrustedNameNumDict(Struct):
        name = CharField()
        num = IntegerField()
        struct = BaseHashTable()

    for key in NameNumDict.objects:
        value = NameNumDict.objects.get(key)
        td = TrustedNameNumDict(name=key, num=value, key="name")
        try:
            td.save()
        except ValueError as e:
            print("Cannot save ({}, {}), because {}".format(key, value, e))
    print("Enumerating a trusted string-keyed hash table:")
    for key in TrustedNameNumDict.objects:
        value = TrustedNameNumDict.objects.get(key)
        print("* {key} (hash: {hash})"
              " -> {value}".format(key=key, hash=key.__hash__(), value=value))
