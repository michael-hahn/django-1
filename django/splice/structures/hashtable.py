"""Hash table, synthesizable hash table, and synthesizable dict."""

from collections import UserDict

from django.splice.untrustedtypes import UntrustedInt, UntrustedStr
from django.splice.synthesis import IntSynthesizer, StrSynthesizer


class HashTable(object):
    """
    Our own simple implementation of a hash table (instead of Python's dict).
    This is for demonstration only. Performance can degrade dramatically with
    more insertions since we do not perform rehashing and so more elements will
    be chained in the same bucket as the size of hash table continues to grow.
    """
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
            yield key

    def __len__(self):
        """The size of the hash table."""
        return sum([len(sublist) for sublist in self._hash_table])

    def __contains__(self, item):
        """Called when using the "in" operator."""
        return item in self.keys()


class SynthesizableHashTable(HashTable):
    """
    Inherit from HashTable to create a custom HashTable
    that behaves exactly like a HashTable but the elements
    in the SynthesizableHashTable can be synthesized.
    """
    def synthesize(self, key):
        """
        Synthesize a given key in the hash table only if key already
        exists in the hash table. The synthesized key must ensure that
        the hash of the synthesized key is the same as that of the original.
        The value of the corresponding key does not change. If synthesis
        succeeded, return True. Returns False if key does not exist in the
        hash table (and therefore no synthesis took place). key's hash
        function must be Z3-friendly for synthesis to be possible.
        """
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


class SynthesizableDict(UserDict):
    """
    Inherit from UserDict to create a custom dict that
    behaves exactly like Python's built-in dict but the
    elements in the SynthesizableDict can be synthesized.
    UserDict is a wrapper/adapter class around the built-in
    dict, which makes the painful process of inheriting
    directly from Python's built-in dict class much easier:
    https://docs.python.org/3/library/collections.html#userdict-objects.

    Alternatively, we can use abstract base classes in
    Python's collections.abc module. In this case, we could
    use MutableMapping as a mixin class to inherit. ABC makes
    modifying a data structure's core functionality easier
    than directly modifying it from dict.
    """
    def synthesize(self, key):
        """
        dict does not provide a programmatic way to access
        and overwrite a key in-place. Since UserDict (as well
        as MutableMapping for that matter) uses Python's
        built-in keys, we have to delete the original key.
        """
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
    pass
