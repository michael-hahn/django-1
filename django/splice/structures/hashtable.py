"""Hash table, synthesizable hash table, and synthesizable dict"""
from collections import UserDict

from django.splice.untrustedtypes import UntrustedInt, UntrustedStr
from django.splice.synthesis import IntSynthesizer, StrSynthesizer
from django.splice.structs import BaseSynthesizableStruct


class HashTable(object):
    """Our own simple implementation of a hash table (instead of Python's dict).
    This is for demonstration only. Performance can degrade dramatically with
    more insertions since we do not perform rehashing and so more elements will
    be chained in the same bucket as the size continues to grow."""
    DEFAULT_NUM_BUCKETS = 10

    def __init__(self, *args, **kwargs):
        """A hash table is just a list of lists. Each list represents a bucket."""
        super().__init__(*args, **kwargs)
        self._num_buckets = self.DEFAULT_NUM_BUCKETS
        self._hash_table = [list() for _ in range(self._num_buckets)]

    def __setitem__(self, key, value):
        """Insert a key/value pair into the hash table."""
        hash_key = key.__hash__() % len(self._hash_table)
        key_exists = False
        bucket = self._hash_table[hash_key]
        for i, kv in enumerate(bucket):
            k, v = kv
            if key == k:
                key_exists = True
                bucket[i] = (key, value)
                break
        if not key_exists:
            bucket.append((key, value))

    def __getitem__(self, key):
        """Get the value of a key if key exists."""
        hash_key = key.__hash__() % len(self._hash_table)
        bucket = self._hash_table[hash_key]
        for i, kv in enumerate(bucket):
            k, v = kv
            if key == k:
                return v
        raise KeyError("{key} does not exist in the hash table".format(key=key))

    def __delitem__(self, key):
        """Delete a key/value pair if key exists; otherwise do nothing."""
        hash_key = key.__hash__() % len(self._hash_table)
        bucket = self._hash_table[hash_key]
        for i, kv in enumerate(bucket):
            k, v = kv
            if key == k:
                del bucket[i]
                break

    def keys(self):
        """All keys in the hash table."""
        return [key for sublist in self._hash_table for (key, value) in sublist]

    def __iter__(self):
        """Iterator over the hash table."""
        for key in self.keys():
            yield key, self.__getitem__(key)

    def __len__(self):
        """The size of the hash table."""
        return sum([len(sublist) for sublist in self._hash_table])

    def __contains__(self, item):
        """Called when using the in operator."""
        return item in self.keys()


class SynthesizableHashTable(HashTable, BaseSynthesizableStruct):
    """Inherit from HashTable to create a custom HashTable
    that behaves exactly like a HashTable but the elements
    in the SynthesizableHashTable can be synthesized."""
    def synthesize(self, key):
        """Synthesize a given key in the hash table only if key already
        exists in the hash table. The synthesized key must ensure that
        the hash of the synthesized key is the same as that of the original.
        The value of the corresponding key does not change. If synthesis
        succeeded, return True. Returns False if key does not exist in the
        hash table (and therefore no synthesis took place). key's hash
        function must be Z3-friendly for synthesis to be possible.

        Here we inherit HashTable before BaseSynthesizableStruct
        for the same reason as in SynthesizableIntSet."""
        hash_key = key.__hash__() % len(self._hash_table)
        bucket = self._hash_table[hash_key]
        for i, kv in enumerate(bucket):
            k, v = kv
            if key == k:
                synthesize_type = type(key).__name__
                # Unlike other data structures, hashtable can
                # take only UntrustedInt or UntrustedStr as keys
                if synthesize_type == 'UntrustedInt':
                    synthesizer = IntSynthesizer()
                    synthesizer.eq_constraint(UntrustedInt.custom_hash, key.__hash__())
                elif synthesize_type == 'UntrustedStr':
                    synthesizer = StrSynthesizer()
                    synthesizer.eq_constraint(UntrustedStr.custom_hash, key.__hash__())
                else:
                    raise NotImplementedError("We cannot synthesize value of type "
                                              "{type} yet".format(type=synthesize_type))

                synthesized_key = synthesizer.to_python(synthesizer.value)
                # Overwrite the original key with the synthesized key
                # We do not overwrite value but only set the synthesized flag
                v.synthesized = True
                bucket[i] = (synthesized_key, v)
                return True
        return False

    def __save__(self, cleaned_data):
        """BaseSynthesizableStruct enforces implementation of
        this method. A subclass of this class can also override
        this method for a customized store.

        The default behavior is that cleaned_data contains a key
        and a value where the key is prefixed by 'key_' and this
        key/value pair is to be inserted into the hash table."""
        if len(cleaned_data) != 2:
            raise ValueError("By default, only one key and one value can be "
                             "inserted at a time using save(). You may want "
                             "to override __save__() for customized insertion.")
        k = None
        v = None
        for key, value in cleaned_data.items():
            if key.startswith('key_'):
                k = value
            else:
                v = value
        if not k or not v:
            raise ValueError("Either key or value is not provided to save()."
                             "You must make sure a key value is prefixed by"
                             "'key_' and a value value is not.")
        self.__setitem__(key=k, value=v)

    def get(self, key):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        obtain data from SynthesizableHashTable."""
        return self.__getitem__(key)

    def delete(self, key):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        remove data from SynthesizableHashTable."""
        return self.__delitem__(key)


class SynthesizableDict(BaseSynthesizableStruct, UserDict):
    """Inherit from UserDict to create a custom dict that
    behaves exactly like Python's built-in dict but the
    elements in the SynthesizableDict can be synthesized.
    UserDict is a wrapper/adapter class around the built-in
    dict, which makes the painful process of inheriting
    directly from Python's built-in dict class much easier.
    Reference:
    https://docs.python.org/3/library/collections.html#userdict-objects.

    Alternatively, we can use abstract base classes in
    Python's collections.abc module. In this case, we could
    use MutableMapping as a mixin class to inherit. ABC makes
    modifying a data structure's core functionality easier
    than directly modifying it from dict.

    Here we inherit BaseSynthesizableStruct before UserDict
    because UserDict is not designed for multi-inheritance."""
    def get(self, key):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        obtain data from SynthesizableDict."""
        return self.data[key]

    def __save__(self, cleaned_data):
        """BaseSynthesizableStruct enforces implementation of
        this method. A subclass of this class can also override
        this method for a customized store.

        The default behavior is that cleaned_data contains a key
        and a value where the key is prefixed by 'key_' and this
        key/value pair is to be inserted into the hash table."""
        if len(cleaned_data) != 2:
            raise ValueError("By default, only one key and one value can be "
                             "inserted at a time using save(). You may want "
                             "to override __save__() for customized insertion.")
        k = None
        v = None
        for key, value in cleaned_data.items():
            if key.startswith('key_'):
                k = value
            else:
                v = value
        if not k or not v:
            raise ValueError("Either key or value is not provided to save()."
                             "You must make sure a key value is prefixed by"
                             "'key_' and a value value is not.")
        self.data[k] = v

    def delete(self, key):
        """BaseSynthesizableStruct enforces implementation of
        this method. This is the public-facing interface to
        remove data from SynthesizableDict."""
        del self.data[key]

    def synthesize(self, key):
        """dict does not provide a programmatic way to access
        and overwrite keys in-place. Since UserDict (as well
        as MutableMapping for that matter) uses Python
        built-in key, we have to delete the original key."""
        if key not in self.data:
            return False
        val = self.data[key]

        synthesize_type = type(key).__name__
        # Unlike other data structures, hashtable can
        # take only UntrustedInt or UntrustedStr as keys
        if synthesize_type == 'UntrustedInt':
            synthesizer = IntSynthesizer()
            synthesizer.eq_constraint(UntrustedInt.custom_hash, key.__hash__())
        elif synthesize_type == 'UntrustedStr':
            synthesizer = StrSynthesizer()
            synthesizer.eq_constraint(UntrustedStr.custom_hash, key.__hash__())
        else:
            raise NotImplementedError("We cannot synthesize value of type "
                                      "{type} yet".format(type=synthesize_type))

        synthesized_key = synthesizer.to_python(synthesizer.value)
        # synthesized_key and key should have the same hash value
        # TODO: Note that if synthesized_key happens to be the same as
        #  the original key, this insertion does nothing. For example,
        #  because of the default hash function of UntrustedInt, the
        #  synthesized int might be the same as the original int key, so
        #  this insertion does not have any effect.
        val.synthesized = True
        self.data[synthesized_key] = val
        del self.data[key]


if __name__ == "__main__":
    from django.forms.fields import CharField, IntegerField

    class NameNumHashTable(SynthesizableHashTable):
        key_name = CharField()
        num = IntegerField()

    sd = NameNumHashTable()
    sd.save(key_name="Jake", num=7)
    sd.save(key_name="Blair", num=5)
    sd.save(key_name="Luke", num=14)
    sd.save(key_name="Andre", num=9)
    sd.save(key_name="Zack", num=12)
    print("Enumerating a string-keyed hash table:")
    for key, value in sd:
        print("* {key} (hash: {hash}) -> {value}".format(key=key, hash=key.__hash__(), value=sd.get(key)))
    sd.synthesize("Blair")
    print("After deleting 'Blair' by synthesis, enumerate again:")
    for key, value in sd:
        print("* {key}(hash: {hash}) -> {value} [Synthesized: {synthesis}]".format(key=key,
                                                                                   hash=key.__hash__(),
                                                                                   value=sd.get(key),
                                                                                   synthesis=key.synthesized))

    class NumNameHashTable(SynthesizableHashTable):
        name = CharField()
        key_num = IntegerField()

    sd = NumNameHashTable()
    sd.save(key_num=7, name="Jake")
    # We need a super big integer key so that the synthesized integer
    # value would be different from this original value
    sd.save(key_num=32345435432758439203535345435, name="Blair")
    sd.save(key_num=14, name="Luke")
    sd.save(key_num=9, name="Andre")
    sd.save(key_num=12, name="Zack")
    print("Enumerating an int-keyed hash table:")
    for key, value in sd:
        print("* {key} (hash: {hash}) -> {value}".format(key=key, hash=key.__hash__(), value=sd.get(key)))
    sd.synthesize(32345435432758439203535345435)
    print("After deleting '32345435432758439203535345435' by synthesis, enumerate again:")
    for key, value in sd:
        print("* {key} (hash: {hash}) -> {value} [Synthesized Key: {synthesis}]".format(key=key,
                                                                                        hash=key.__hash__(),
                                                                                        value=sd.get(key),
                                                                                        synthesis=key.synthesized))

    class NameNumHashTable(SynthesizableDict):
        key_name = CharField()
        num = IntegerField()

    sd = NameNumHashTable()
    sd.save(key_name="Jake", num=7)
    sd.save(key_name="Blair", num=5)
    sd.save(key_name="Luke", num=14)
    sd.save(key_name="Andre", num=9)
    sd.save(key_name="Zack", num=12)
    print("Enumerating a string-keyed hash table:")
    for key, value in sd.items():
        print("* {key} (hash: {hash}) -> {value}".format(key=key, hash=key.__hash__(), value=sd.get(key)))
    sd.synthesize("Luke")
    print("After deleting 'Luke' by synthesis, enumerate again:")
    for key, value in sd.items():
        print("* {key}(hash: {hash}) -> {value} [Synthesized: {synthesis}]".format(key=key,
                                                                                   hash=key.__hash__(),
                                                                                   value=sd.get(key),
                                                                                   synthesis=key.synthesized))

    sd.delete("Andre")
    print("After deleting 'Andre' by calling delete(), enumerate again:")
    for key, value in sd.items():
        print("* {key}(hash: {hash}) -> {value} [Synthesized: {synthesis}]".format(key=key,
                                                                                   hash=key.__hash__(),
                                                                                   value=sd.get(key),
                                                                                   synthesis=key.synthesized))
