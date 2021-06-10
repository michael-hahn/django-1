"""Hash table, synthesizable hash table, and synthesizable dict."""
# from django.splice.replace import replace
from collections import UserDict

from django.splice.splicetypes import SpliceInt, SpliceStr
from django.splice.synthesis import IntSynthesizer, StrSynthesizer
from django.splice.structs import SpliceStructMixin


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
                # take only SpliceInt or SpliceStr as keys
                if synthesize_type == 'SpliceInt':
                    synthesizer = IntSynthesizer()
                    synthesizer.eq_constraint(SpliceInt.custom_hash, key.__hash__())
                elif synthesize_type == 'SpliceStr':
                    synthesizer = StrSynthesizer()
                    synthesizer.eq_constraint(SpliceStr.custom_hash, key.__hash__())
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
        # take only SpliceInt or SpliceStr as keys
        if synthesize_type == 'SpliceInt':
            synthesizer = IntSynthesizer()
            synthesizer.eq_constraint(SpliceInt.custom_hash, key.__hash__())
        elif synthesize_type == 'SpliceStr':
            synthesizer = StrSynthesizer()
            synthesizer.eq_constraint(SpliceStr.custom_hash, key.__hash__())
        else:
            raise NotImplementedError("We cannot synthesize value of type "
                                      "{type} yet".format(type=synthesize_type))

        synthesized_key = synthesizer.to_python(synthesizer.value)
        # synthesized_key and key should have the same hash value
        # TODO: Note that if synthesized_key happens to be the same as
        #  the original key, this insertion does nothing. For example,
        #  because of the default hash function of SpliceInt, the
        #  synthesized int might be the same as the original int key, so
        #  this insertion does not have any effect.
        val.synthesized = True
        self.data[synthesized_key] = val
        del self.data[key]


class SpliceDict(SpliceStructMixin, UserDict):
    """
    Inherit from UserDict to create a custom dict that
    behaves exactly like Python's built-in dict but 1)
    any insertion converts input data into an untrusted
    Splice value if possible; 2) gives symbolic constraints
    to keys by defining this structure as their referrers;
    and 3) defines additional method (hash) that will be
    invoked during constraint concretization.
    """
    def enclosing(self, obj):
        """Not needed in this data structure, but we must define here."""
        pass

    def __setitem__(self, key, item):
        """
         Convert value into an untrusted Splice value. Only
         give "key" symbolic constraints because constraints
         defined in this data structure are only for keys.
         We then UserDict's __setitem__ to perform actual insert.
         """
        key = self.splicify(key, concretize_cb=self.concretize_cb("eq(hash, hash())"))
        item = self.splicify(item, concretize_cb=None)
        super().__setitem__(key, item)

    # Method called by synthesis constraints ===========
    @staticmethod
    def hash(item):
        """
        This method is used as function input to "eq"
        constraint. Technically this hash should also be
        the one that SpliceStr uses to hash itself for
        the dict, so that the original and the synthesized
        strings both have the same hash value through the
        same hash function.
        """
        if isinstance(item, str):
            item = bytes(item, 'ascii')
        h = 0
        for byte in item:
            h = h * 31 + byte
        return h


if __name__ == "__main__":
    from django.splice.splicetypes import SpliceMixin, SpliceInt
    from django.splice.identity import empty_taint
    from django.splice.synthesis import init_synthesizer
    from django.splice.constraints import merge_constraints
    import gc
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django.settings")

    # Set up a SpliceDict instance
    taint = empty_taint()
    taint[30] = True
    ka = SpliceStr("ABCDE", trusted=True, synthesized=False, taints=taint)
    va = SpliceInt(12345, trusted=True, synthesized=False, taints=taint)
    kb = SpliceStr("FGHI", trusted=True, synthesized=False, taints=taint)
    vb = SpliceInt(9876, trusted=True, synthesized=False, taints=taint)
    kc = SpliceStr("JKLM", trusted=True, synthesized=False, taints=taint)
    vc = SpliceInt(34567, trusted=True, synthesized=False, taints=taint)
    taint2 = empty_taint()
    taint2[8] = True
    kd = SpliceStr("NOPQR", trusted=True, synthesized=False, taints=taint2)
    vd = SpliceInt(12456, trusted=True, synthesized=False, taints=taint2)
    d = SpliceDict()
    d[ka] = va
    d[kb] = vb
    d[kc] = vc
    d[kd] = vd

    # Test GC
    objs = gc.get_objects()
    for obj in objs:
        # Only Splice objects with the taint of the user to be deleted need to be synthesized.
        if isinstance(obj, SpliceMixin) and obj.taints == taint:
            # Perform Splice object deletion through synthesis.
            synthesizer = init_synthesizer(obj)
            # Concretize constraints for obj using symbolic constraints from its
            # enclosing data structure.
            concrete_constraints = []
            for constraint in obj.constraints:
                concrete_constraints.append(constraint(obj))
            # Merge all concrete constraints, if needed
            if not concrete_constraints:
                merged_constraints = None
            else:
                merged_constraints = concrete_constraints[0]
                for concrete_constraint in concrete_constraints[1:]:
                    merged_constraints = merge_constraints(merged_constraints, concrete_constraint)
            # Synthesis handles setting trusted and synthesized flags properly
            synthesized_obj = synthesizer.splice_synthesis(merged_constraints)
            if synthesized_obj is not None:
                # If synthesis was successful, replace the original obj with the synthesized object.
                replace(obj, synthesized_obj)
            else:
                # If synthesis failed for some reason, the best we can do is to change object attributes.
                obj.trusted = False
                obj.synthesized = True
                obj.taints = empty_taint()
                obj.constraints = []
