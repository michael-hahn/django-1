from django.splice.untrustedtypes import UntrustedInt, UntrustedStr, UntrustedMixin
from django.splice.synthesis import IntSynthesizer, StrSynthesizer, init_synthesizer

from collections import UserDict
from sortedcontainers import SortedList
import heapq


class BiNode(object):
    """Node class with two children."""
    def __init__(self, val, *, key=None):
        """Use key for organization if exists; otherwise, use val."""
        self._val = val
        self._key = key
        self._left = None
        self._right = None

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, val):
        self._val = val

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    def has_key(self):
        return bool(self._key)

    @property
    def left_child(self):
        return self._left

    @left_child.setter
    def left_child(self, node):
        self._left = node

    @property
    def right_child(self):
        return self._right

    @right_child.setter
    def right_child(self, node):
        self._right = node


class BinarySearchTree(object):
    """BST using BiNode."""
    def __init__(self):
        self.root = None

    def insert(self, val, key=None):
        """Insert a value (or key/value pair if keys are used) to a BST.
        Returns False if insertion failed (e.g., if a key/value pair
        is given to be inserted into a value-only tree). This is the
        public API to construct a new tree or add new nodes to an existing tree."""
        if self.root is None:
            self._set_root(val, key)
        else:
            # BST nodes either all have a key or none of the nodes have a key!
            if self.root.has_key() and not key:
                return False
            elif not self.root.has_key() and key:
                return False
            else:
                self._insert_node(self.root, val, key)

    def _set_root(self, val, key=None):
        """Application should not call this function directly.
        Always call the public API insert() to construct a new tree."""
        self.root = BiNode(val, key=key)

    def _insert_node(self, curr, val, key=None):
        """Only unique values (or keys if exist) inserted modify the tree.
        If insertion is not successful (e.g., val is the same as a node
        already in the tree), it returns False. Application should not call
        this function directly. Always call the public API insert() to add
        new nodes to an existing tree."""
        if key and key < curr.key or not key and val < curr.val:
            if curr.left_child:
                self._insert_node(curr.left_child, val, key)
            else:
                curr.left_child = BiNode(val, key=key)
        elif key and key > curr.key or not key and val > curr.val:
            if curr.right_child:
                self._insert_node(curr.right_child, val, key)
            else:
                curr.right_child = BiNode(val, key=key)
        else:
            return False

    def get(self, key):
        """If the BST has both a key and a value in a node,
        returns the value for a given key if the key exists.
        Otherwise, return None."""
        n = self.find(key)
        return n.val

    def find(self, key_or_val):
        """Return the node if value (or key if exists) is in the
        tree; otherwise, return None. This is the public API to
        find a node in a tree."""
        return self._find_node(self.root, key_or_val)

    def _find_node(self, curr, key_or_val):
        """Find a node based on the given value (or key if exists).
        Returns None if the value (or key) does not exist in the
        tree. Application should call the public API find() instead."""
        if not curr:
            return None
        curr_val = curr.val
        if curr.key:
            curr_val = curr.key

        if key_or_val == curr_val:
            return curr
        elif key_or_val > curr_val:
            return self._find_node(curr.right_child, key_or_val)
        else:
            return self._find_node(curr.left_child, key_or_val)

    def delete(self, key_or_val):
        """Modify the tree by removing a node if it has the
        given value (or key if exists). Otherwise, do nothing.
        This is the public API to delete a node in a tree."""
        self.root = self._delete_node(self.root, key_or_val)

    def _delete_node(self, curr, key_or_val):
        """Find a node based on the given value (or key if exists)
        and delete the node from the tree if it exists. Application
        should call the public API delete() instead."""
        if curr is None:
            return curr
        curr_val = curr.val
        if curr.has_key():
            curr_val = curr.key

        if key_or_val < curr_val:
            curr.left_child = self._delete_node(curr.left_child, key_or_val)
        elif key_or_val > curr_val:
            curr.right_child = self._delete_node(curr.right_child, key_or_val)
        else:
            if curr.left_child is None:
                return curr.right_child
            elif curr.right_child is None:
                return curr.left_child
            candidate = self._min_value_node(curr.right_child)

            curr.val = candidate.val
            key_or_val = candidate.val
            if curr.has_key():
                curr.key = candidate.key
                key_or_val = candidate.key
            curr.right_child = self._delete_node(curr.right_child, key_or_val)
        return curr

    def _max_value_node(self, node):
        """The node with the maximum value (or key if exists) of a (sub)tree
        rooted at node. The maximum value is the node itself if it has no
        right subtree."""
        if node is None:
            return None
        if node.right_child:
            return self._max_value_node(node.right_child)
        return node

    def _max_value(self, node):
        """The maximum value (or key if exists) of a (sub)tree rooted at node.
        The maximum value is the node itself if it has no right subtree."""
        max_node = self._max_value_node(node)
        if max_node is None:
            return False
        if max_node.has_key():
            return max_node.key
        else:
            return max_node.val

    def _min_value_node(self, node):
        """The node with the minimum value (or key if exists) of a (sub)tree
        rooted at node. The minimum value is the node itself if it has no
        left subtree."""
        if node is None:
            return None
        if node.left_child:
            return self._min_value_node(node.left_child)
        else:
            return node

    def _min_value(self, node):
        """The minimum value (or key if exists) of a (sub)tree rooted at node.
        The minimum value is the node itself if it has no left subtree."""
        min_node = self._min_value_node(node)
        if min_node is None:
            return False
        if min_node.has_key():
            return min_node.key
        else:
            return min_node.val

    def synthesize(self, node):
        """Synthesize the val (or key if exists) of a node.
        Only performs bounded value synthesis if both upper
        and lower bound exist for the node. Otherwise, create
        an Untrusted val (or key if exists) of the same value
        and with the synthesized flag set. If synthesis
        failed for any reason, return False. If synthesis
        succeeded, return True."""
        upper_bound = self._min_value(node.right_child)
        lower_bound = self._max_value(node.left_child)
        # Initialize a synthesizer based on the type of
        # either the key (if exists) or val
        value = node.val
        if node.key:
            value = node.key
        synthesizer = init_synthesizer(value)

        # If at most one bound exists, do simple synthesis
        if not upper_bound or not lower_bound:
            if node.key:
                synthesized_value = synthesizer.simple_synthesis(node.key)
            else:
                synthesized_value = synthesizer.simple_synthesis(node.val)
        else:
            # Do bounded synthesis if both bounds exist
            synthesized_value = synthesizer.bounded_synthesis(upper_bound=upper_bound,
                                                              lower_bound=lower_bound)

        # Some synthesis can fail; synthesis
        # failed if synthesized_value is None
        if synthesized_value is None:
            return False
        # Finally, if synthesis succeeded, replace the val
        # (or key if exists) with the synthesized value.
        else:
            if node.key:
                node.key = synthesized_value
                node.val = None
            else:
                node.val = synthesized_value
        return True

    def to_ordered_list(self, node, ordered_list):
        """Convert the tree into an in-ordered list of nodes.
        The list is stored at ordered_list parameter."""
        if node is None:
            return ordered_list

        if node.left_child:
            self.to_ordered_list(node.left_child, ordered_list)
        ordered_list.append(node)
        if node.right_child:
            self.to_ordered_list(node.right_child, ordered_list)

    def __str__(self):
        """Print out the tree in-order."""
        ordered_list = list()
        self.to_ordered_list(self.root, ordered_list)
        printout = ""
        for node in ordered_list:
            if node.key:
                printout += "{key}({value}) ".format(key=node.key, value=node.val)
            else:
                printout += "{value} ".format(value=node.val)
        return printout


class SynthesizableSortedList(SortedList):
    """Inherit from SortedList to create a custom sorted list
    that behaves exactly like a sorted list (with elements sorted
    in the list) but the elements in the SynthesizableSortedList
    can be synthesized. Reference of the sorted containers:
    http://www.grantjenks.com/docs/sortedcontainers/sortedlist.html."""
    def __setitem__(self, index, value):
        """SortedList raise not-implemented error when calling
        __setitem__ because it will not allow users to simply
        replace a value at index (in case the list becomes
        unsorted). We implement this function based on SortedList
        __getitem__ implementation for direct replacement so that
        synthesis can replace a value directly. Note that our
        synthesis guarantees the sorted order so it is OK to do
        so, but the user of SynthesizableSortedList should not
        call this function.

        This function is implemented specifically for our synthesis.
        One should not use this function to e.g., append a new value.

        Note that We are unfortunately using many supposedly
        "protected" instance attributes to implement __setitem__."""
        _lists = self._lists
        _maxes = self._maxes

        pos, idx = self._pos(index)
        _lists[pos][idx] = value
        # SortedList maintains a list of maximum values for each sublist.
        # We must update the maximum value if "value" becomes the
        # maximum value of its sublist.
        if idx == len(_lists[pos]) - 1:
            _maxes[pos] = value

    def synthesis(self, index):
        """Synthesize a value at a given index in the sorted list.
        The synthesized value must ensure that the list is still sorted.
        If synthesis succeeded, return True."""
        if index >= self._len or index < 0:
            raise IndexError('list index out of range')

        value = self.__getitem__(index)
        synthesizer = init_synthesizer(value)

        if index == 0:
            # The value to be synthesized is the smallest in the sorted list
            synthesizer.lt_constraint(self.__getitem__(index + 1))
        elif index == self._len - 1:
            # The value to be synthesized is the largest in the sorted list
            synthesizer.gt_constraint(self.__getitem__(index - 1))
        else:
            # The value to be synthesized is in the middle of the sorted list
            synthesizer.bounded_constraints(upper_bound=self.__getitem__(index + 1),
                                            lower_bound=self.__getitem__(index - 1))
        synthesized_value = synthesizer.to_python(synthesizer.value)
        self.__setitem__(index, synthesized_value)
        return True


class SynthesizableDict(UserDict):
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
    than directly modifying it from dict."""
    def synthesis(self, key):
        """dict does not provide a programmatic way to
        access and overwrite keys in-place. Since UserDict
        (as well as MutableMapping for that matter) uses
        Python's built-in key, we cannot do a real
        synthesis. We will do a "fake" one just to illustrate,
        but something still won't work in this data structure."""
        if key not in self.data:
            return True
        val = self.data[key]
        synthesizer = init_synthesizer(val)

        synthesized_value = synthesizer.to_python(synthesizer.value)
        # synthesized_value and key should have the same hash value
        # TODO: Note that if synthesized_value happens to be the same as
        #  the original key, this insertion does nothing. For example,
        #  because of the default hash function of UntrustedInt, the
        #  synthesized int might be the same as the original int key, so
        #  this insertion does not have any effect.
        self.data[synthesized_value] = val


class SynthesizableHashTable(object):
    """Our own simple implementation of a hash table (instead of Python's dict).
    This is for demonstration only. Performance can degrade dramatically with
    more insertions since we do not perform rehashing and so more elements will
    be chained in the same bucket as the size continues to grow."""
    DEFAULT_NUM_BUCKETS = 10

    def __init__(self):
        """A hash table is just a list of lists. Each list represents a bucket."""
        self._num_buckets = self.DEFAULT_NUM_BUCKETS
        self._hash_table = [list() for _ in range(self._num_buckets)]

    def __setitem__(self, key, value):
        """Insert a key/value pair into the hash table. Only keys of
        Untrusted types can be inserted since we use Z3-friendly hash
        function defined in those types."""
        if not issubclass(type(key), UntrustedMixin):
            raise KeyError("Only Untrusted-typed keys allowed. This key "
                           "of type {type} is not.".format(type=type(key)))

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
        key_exists = False
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

    def synthesis(self, key):
        """Synthesize a given key in the hash table only if key already
        exists in the hash table. The synthesized key must ensure that
        the hash of the synthesized key is the same as that of the original.
        The value of the corresponding key does not change. If synthesis
        succeeded, return True. Returns False if key does not exist in the
        hash table (and therefore no synthesis took place)."""
        hash_key = key.__hash__() % len(self._hash_table)
        bucket = self._hash_table[hash_key]
        for i, kv in enumerate(bucket):
            k, v = kv
            if key == k:
                synthesize_type = type(key).__name__
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
                bucket[i] = (synthesized_key, v)
                return True
        return False


class SynthesizableMinHeap(object):
    """A binary min heap for which a[k] <= a[2*k+1] and a[k] <= a[2*k+2] for
    all k, counting elements from 0. For the sake of comparison, non-existing
    elements are considered to be infinite.  The interesting property of a
    heap is that a[0] is always its smallest element. See docstring from heapq.py."""
    def __init__(self, initial=[]):
        """Defaults to an empty heap. Initial can also be
        a list, which could be transformed into a heap."""
        self._heap = initial
        heapq.heapify(self._heap)

    def insert(self, item):
        """Insert item into the heap while maintaining heap invariance."""
        heapq.heappush(self._heap, item)

    def pop(self):
        """Pop the smallest item off the heap, while maintaining heap invariant."""
        return heapq.heappop(self._heap)

    def peek(self):
        """Return the smallest item from the heap (if exists),
        without popping it out. Otherwise, return None."""
        if len(self._heap) > 0:
            return self._heap[0]
        return None

    def to_list(self):
        """Return a list of all elements in the heap."""
        return self._heap

    def synthesize(self, index):
        """Synthesize a new value at index without invalidating heap invariant.
        The synthesized value must be smaller than both children (if exist) and
        larger than its parent (if exists). Returns True if synthesis succeeds.

        Important Note: Unlike insertion, synthesis must explicitly ensure that
        the value is smaller than its parent!"""
        if index >= len(self._heap) or index < 0:
            raise IndexError('list index out of range')

        value = self._heap[index]
        synthesizer = init_synthesizer(value)

        # Get the parent and children value if exist
        parent_index = (index-1) // 2
        parent_value = None
        if parent_index >= 0:
            parent_value = self._heap[parent_index]
        left_child_index = 2 * index + 1
        left_child_value = None
        if left_child_index < len(self._heap):
            left_child_value = self._heap[left_child_index]
        right_child_index = 2 * index + 2
        right_child_value = None
        if right_child_index < len(self._heap):
            right_child_value = self._heap[right_child_index]

        # lower_bound can be None if the value to be synthesized is root
        lower_bound = parent_value
        # upper_bound can be None if the value has no children
        upper_bound = left_child_value
        if left_child_value is None:
            upper_bound = right_child_value
        elif right_child_value is not None:
            upper_bound = min(left_child_value, right_child_value)

        # For leaf nodes
        if lower_bound and not upper_bound:
            synthesizer.gt_constraint(lower_bound)
        # For root node
        elif upper_bound and not lower_bound:
            synthesizer.lt_constraint(upper_bound)
        # For all other nodes
        else:
            synthesizer.bounded_constraints(upper_bound=upper_bound,
                                            lower_bound=lower_bound)
        synthesized_value = synthesizer.to_python(synthesizer.value)
        self._heap[index] = synthesized_value
        return True

    def __str__(self):
        """The contents of the heap."""
        heap = str()
        for i in range(0, (len(self._heap) // 2)):
            if 2*i+2 < len(self._heap):
                heap += "[{parent}] -> [{left}  {right}]\n".format(parent=self._heap[i],
                                                                   left=self._heap[2*i+1],
                                                                   right=self._heap[2*i+2])
            else:
                heap += "[{parent}] -> [{left} ]".format(parent=self._heap[i],
                                                         left=self._heap[2 * i + 1])
        return heap


class IntSet(object):
    """Python implementation of Redis' intSet data structure (simplified).
    A quick introduction can be found here:
    http://blog.wjin.org/posts/redis-internal-data-structure-intset.html
    Original C code reference (v5.0.0) can be found here:
    http://blog.wjin.org/posts/redis-internal-data-structure-intset.html.
    Unlike the original implementation, we will always use big endian."""
    # Different encodings use different numbers of bytes
    INTSET_ENC_INT16 = 2
    INTSET_ENC_INT32 = 4
    INTSET_ENC_INT64 = 8
    # Min/max integer value for different encodings
    INT16_MIN = -32768
    INT16_MAX = 32767
    INT32_MIN = -2_147_483_648
    INT32_MAX = 2_147_483_647

    def __init__(self):
        """Initialize an intSet with default int16 encoding, which
        can be upgraded to int32 and then int64 later if needed.
        self._length is the number of actual integers in intSet, *not*
        the length of self._contents. Each element in self._contents
        is an int8 value."""
        self._encoding = IntSet.INTSET_ENC_INT16
        self._length = 0
        self._contents = list()

    @staticmethod
    def _get_encoding(value):
        """Return the required encoding for the provided value."""
        if value < IntSet.INT32_MIN or value > IntSet.INT32_MAX:
            return IntSet.INTSET_ENC_INT64
        elif value < IntSet.INT16_MIN or value > IntSet.INT16_MAX:
            return IntSet.INTSET_ENC_INT32
        else:
            return IntSet.INTSET_ENC_INT16

    def __getitem__(self, pos, encoding):
        """Return the value at pos, using the configured encoding.
        Note that pos is in terms of the set visible to the user,
        it is not the location in self._contents (i.e., pos would
        correspond to self._length)."""
        return int.from_bytes(self._contents[pos*encoding:(pos+1)*encoding], byteorder='big', signed=True)

    def __setitem__(self, pos, value, encoding):
        """Set the value at pos using the configured encoding.
        Note that pos is in terms of the set visible to the user,
        it is not the location in self._contents (i.e., pos would
        correspond to self._length)."""
        byte_arr = [int(i) for i in value.to_bytes(self._encoding, byteorder='big', signed=True)]
        for i in range(pos*encoding, (pos+1)*encoding):
            self._contents[i] = byte_arr[i-pos*encoding]

    def __len__(self):
        """Return the number of elements in the intSet."""
        return self._length

    def _search(self, value):
        """Search for the position of "value". Returns a tuple (1, pos)
        if the value was found and pos would be the position of the value
        within the intSet (note that values are sorted); otherwise, return
        (0, pos) if the value is not present in the intSet and pos is
        the position where value can be inserted."""
        if self._length == 0:
            # We cannot find any value if intSet is empty
            return 0, 0
        else:
            # Cases where we know we cannot find the
            # value but we know the insertion position.
            if value > self.__getitem__(self._length-1, self._encoding):
                return 0, self._length
            elif value < self.__getitem__(0, self._encoding):
                return 0, 0

        # Try to locate the position of the value in intSet using binary search
        min_pos, max_pos, mid_pos = 0, self._length - 1, -1
        while max_pos >= min_pos:
            mid_pos = (min_pos + max_pos) >> 1
            cur = self.__getitem__(mid_pos, self._encoding)
            if value > cur:
                min_pos = mid_pos + 1
            elif value < cur:
                max_pos = mid_pos - 1
            else:
                break

        if value == cur:
            return 1, mid_pos
        else:
            return 0, min_pos

    def find(self, value):
        """Determine whether value belongs to this intSet."""
        value_encoding = IntSet._get_encoding(value)
        return value_encoding <= self._encoding and self._search(value)[0]

    def _upgrade_and_add(self, value):
        """Upgrades the intSet to a larger encoding and inserts the given integer."""
        # "prepend" is used to make sure we have an empty
        # space at either the beginning or the end of intSet
        prepend = 1 if value < 0 else 0

        # Change the encoding and resize self._contents
        old_encoding = self._encoding
        self._encoding = IntSet._get_encoding(value)
        # Size difference from existing elements: self._length * (self._encoding - old_encoding)
        # Plus space for the added value: self._encoding
        self._contents.extend([None] * (self._length * (self._encoding - old_encoding) + self._encoding))

        # Upgrade back-to-front so we don't overwrite values.
        for i in range(self._length-1, -1, -1):
            self.__setitem__(i+prepend, self.__getitem__(i, old_encoding), self._encoding)
        # Set value at the beginning or the end
        if prepend:
            self.__setitem__(0, value, self._encoding)
        else:
            self.__setitem__(self._length, value, self._encoding)
        # Update the length after insertion
        self._length += 1

    def _move_tail(self, from_pos, to_pos):
        """Move elements starting from from_pos position to
        locations starting from to_pos position in intSet."""
        bytes_to_move = (self._length - from_pos) * self._encoding
        # src, dst are locations in self._contents
        src = self._encoding * from_pos
        dst = self._encoding * to_pos
        # Move in different directions to avoid overwriting values
        if src > dst:
            for i in range(bytes_to_move):
                self._contents[dst+i] = self._contents[src+i]
        elif src < dst:
            for i in range(bytes_to_move-1, -1, -1):
                self._contents[dst+i] = self._contents[src+i]

    def add(self, value):
        """Insert an integer in intSet."""
        value_encoding = IntSet._get_encoding(value)

        # Upgrade encoding if necessary. If we need to upgrade, we know that
        # this value should be either appended (if > 0) or prepended (if < 0),
        # because it lies outside the range of existing values.
        if value_encoding > self._encoding:
            return self._upgrade_and_add(value)
        else:
            # Do nothing if value is already in the set
            exist, pos = self._search(value)
            if exist:
                return
            self._contents.extend([None] * self._encoding)
            if pos < self._length:
                self._move_tail(pos, pos+1)

        self.__setitem__(pos, value, self._encoding)
        self._length += 1

    def delete(self, value):
        """Delete an integer from intSet."""
        value_encoding = IntSet._get_encoding(value)

        if value_encoding <= self._encoding:
            exist, pos = self._search(value)
            if exist:
                # Overwrite value with tail and update length
                if pos < self._length-1:
                    self._move_tail(pos+1, pos)
                # Remove the last value represented in .contents
                for i in range(self._encoding):
                    self._contents.pop(len(self._contents)-1)
                self._length -= 1

    def __str__(self):
        """The contents of intSet."""
        set_str = "[ "
        for i in range(self._length):
            set_str += str(self.__getitem__(i, self._encoding)) + " "
        set_str += "]"
        return set_str


class SynthesizableIntSet(IntSet):
    """Inherit from IntSet to create a custom IntSet
    that behaves exactly like a IntSet (with elements sorted
    in the list) but the elements in the SynthesizableIntSet
    can be synthesized. We intentionally did not add
    the synthesis feature in the IntSet superclass (even
    though we implemented it ourselves) because we want to
    highlight the changes that must be done to make IntSet
    synthesizable (and that its unique encoding design
    makes synthesis different from, e.g., a sorted list)."""
    def __getitem__(self, pos, encoding):
        """Override the superclass __getitem__ method
        because we must return an UntrustedInt instead of
        int and we must check if the returned value should
        have synthesized flag set or not."""
        # All values in self._contents should be of type UntrustedInt
        # If any value is synthesized, the entire value should be synthesized
        synthesized = False
        for i in range(pos*encoding, (pos+1)*encoding):
            synthesized = synthesized or self._contents[i].synthesized
        return UntrustedInt(int.from_bytes(self._contents[pos*encoding:(pos+1)*encoding],
                                           byteorder='big', signed=True),
                            synthesized=synthesized)

    def __setitem__(self, pos, value, encoding):
        """Override the superclass __setitem__ method
        because value is converted into a byte array
        to be inserted into the data structure, instead
        of being directly inserted into the data structure.
        We do not want to "lose" the Untrusted type during
        the conversion!"""
        if not issubclass(type(value), UntrustedMixin):
            raise ValueError("Only Untrusted-typed value can be inserted "
                             "into SynthesizableIntSet, but {value} is "
                             "of type {type}".format(value=value,
                                                     type=type(value)))
        synthesized = value.synthesized
        byte_arr = [UntrustedInt(i, synthesized=synthesized)
                    for i in value.to_bytes(self._encoding, byteorder='big', signed=True)]
        for i in range(pos*encoding, (pos+1)*encoding):
            self._contents[i] = byte_arr[i-pos*encoding]

    def synthesize(self, pos):
        """Synthesize a new value at pos (of intSet) without invalidating ordered-set
        invariant. The synthesized value must be smaller than the next value (if exist)
        and larger than the previous one (if exists). Returns True if synthesis succeeds.
        It is possible that the same value is marked as synthesized because no other
        synthesis value is possible.

        Note: Synthesis should not change the encoding of this data structure. Therefore,
        it is possible that a suitable value only exists in a different encoding but
        because we cannot use the value, we would have to use the same value (and mark it
        as synthesized). """
        if pos >= self._length or pos < 0:
            raise IndexError('set index out of range')
        value = self.__getitem__(pos, self._encoding)
        # for intSet, synthesizer should always be an IntSynthesizer
        synthesizer = init_synthesizer(value)
        # Value constraints imposed by the current encoding
        if self._encoding == IntSet.INTSET_ENC_INT16:
            synthesizer.bounded_constraints(upper_bound=IntSet.INT16_MAX,
                                            lower_bound=IntSet.INT16_MIN)
        elif self._encoding == IntSet.INTSET_ENC_INT32:
            synthesizer.bounded_constraints(upper_bound=IntSet.INT32_MAX,
                                            lower_bound=IntSet.INT32_MIN)

        # Value constraints imposed by the position of the value in intSet
        if pos == 0:
            # The value to be synthesized is the smallest in the sorted list
            synthesizer.lt_constraint(self.__getitem__(pos+1, self._encoding))
        elif pos == self._length-1:
            # The value to be synthesized is the largest in the sorted list
            synthesizer.gt_constraint(self.__getitem__(pos-1, self._encoding))
        else:
            # The value to be synthesized is in the middle of the intSet
            synthesizer.bounded_constraints(upper_bound=self.__getitem__(pos+1, self._encoding),
                                            lower_bound=self.__getitem__(pos-1, self._encoding))
        synthesized_value = synthesizer.to_python(synthesizer.value)
        self.__setitem__(pos, synthesized_value, self._encoding)
        return True


def bst_test():
    bst = BinarySearchTree()
    bst.insert(UntrustedStr("Jake"), UntrustedInt(7))
    bst.insert(UntrustedStr("Blair"), UntrustedInt(5))
    bst.insert(UntrustedStr("Luke"), UntrustedInt(14))
    bst.insert(UntrustedStr("Andre"), UntrustedInt(9))
    bst.insert(UntrustedStr("Zack"), UntrustedInt(12))
    print(str(bst))
    print(bst.synthesize(bst.root))
    print(str(bst))

    bst = BinarySearchTree()
    bst.insert(UntrustedStr("Jake"))
    bst.insert(UntrustedStr("Blair"))
    bst.insert(UntrustedStr("Luke"))
    bst.insert(UntrustedStr("Andre"))
    bst.insert(UntrustedStr("Zack"))
    print(str(bst))
    print(bst.synthesize(bst.root))
    print(str(bst))


def sorted_list_test():
    sl = SynthesizableSortedList()
    sl.update([UntrustedStr("Jake"), UntrustedStr("Blair"), UntrustedStr("Luke"),
               UntrustedStr("Andre"), UntrustedStr("Zack")])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)

    sl = SynthesizableSortedList()
    sl.update([UntrustedInt(7), UntrustedInt(5), UntrustedInt(14),
              UntrustedInt(9), UntrustedInt(12)])
    print(sl)
    sl.synthesis(2)
    print(sl)
    sl.synthesis(0)
    print(sl)
    sl.synthesis(4)
    print(sl)


def hash_table_test():
    sd = SynthesizableHashTable()
    sd[UntrustedStr("Jake")] = UntrustedInt(7)
    sd[UntrustedStr("Blair")] = UntrustedInt(5)
    sd[UntrustedStr("Luke")] = UntrustedInt(14)
    sd[UntrustedStr("Andre")] = UntrustedInt(9)
    sd[UntrustedStr("Zack")] = UntrustedInt(12)
    for key, value in sd:
        print("{key} (hash: {hash}) -> {value}".format(key=key, hash=key.__hash__(), value=sd[key]))

    sd.synthesis(UntrustedStr("Blair"))
    print("After deleting 'Blair' by synthesis...")
    for key, value in sd:
        print("{key}(hash: {hash}) -> {value} [Synthesized: {synthesis}]".format(key=key,
                                                                                 hash=key.__hash__(),
                                                                                 value=sd[key],
                                                                                 synthesis=key.synthesized))
    sd = SynthesizableHashTable()
    sd[UntrustedInt(7)] = UntrustedStr("Jake")
    # We need a super big integer key so that the synthesized integer
    # value would be different from this original value
    sd[UntrustedInt(32345435432758439203535345435)] = UntrustedStr("Blair")
    sd[UntrustedInt(14)] = UntrustedStr("Luke")
    sd[UntrustedInt(9)] = UntrustedStr("Andre")
    sd[UntrustedInt(12)] = UntrustedStr("Zack")
    for key, value in sd:
        print("{key} (hash: {hash}) -> {value}".format(key=key, hash=key.__hash__(), value=sd[key]))
    sd.synthesis(UntrustedInt(32345435432758439203535345435))
    print("After deleting '32345435432758439203535345435' by synthesis...")
    for key, value in sd:
        print("{key} (hash: {hash}) -> {value} [Synthesized Key: {synthesis}]".format(key=key,
                                                                                      hash=key.__hash__(),
                                                                                      value=sd[key],
                                                                                      synthesis=key.synthesized))


def min_heap_test():
    mh = SynthesizableMinHeap([UntrustedInt(4), UntrustedInt(3), UntrustedInt(5),
                               UntrustedInt(12), UntrustedInt(5), UntrustedInt(7),
                               UntrustedInt(1)])
    print("Initial min heap:\n{mh}".format(mh=mh))
    mh.synthesize(0)
    print("After synthesis the root node:\n{mh}".format(mh=mh))
    mh.synthesize(2)
    print("After synthesis an intermediate node:\n{mh}".format(mh=mh))

    mh = SynthesizableMinHeap([UntrustedStr("Jake"), UntrustedStr("Blair"), UntrustedStr("Luke"),
                               UntrustedStr("Andre"), UntrustedStr("Zack"), UntrustedStr("Tommy"),
                               UntrustedStr("Sandra")])
    print("Initial min heap:\n{mh}".format(mh=mh))
    mh.synthesize(0)
    print("After synthesis the root node:\n{mh}".format(mh=mh))
    mh.synthesize(2)
    print("After synthesis an intermediate node:\n{mh}".format(mh=mh))


def int_set_test():
    int_set = SynthesizableIntSet()
    int_set.add(UntrustedInt(5))
    int_set.add(UntrustedInt(30))
    int_set.add(UntrustedInt(-7))
    int_set.add(UntrustedInt(14))
    int_set.add(UntrustedInt(5))
    # We should not have access to _contents but it is OK for testing
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.add(UntrustedInt(35267))
    # We expect the intSet to take more space now (int16 -> int32)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.add(UntrustedInt(2_447_483_647))
    # We expect the intSet to take even more space now (int32 -> int64)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.add(UntrustedInt(-335267))
    int_set.add(UntrustedInt(-2_447_483_747))
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    print("45 is in the set: {}".format(int_set.find(45)))
    print("35267 is in the set: {}".format(int_set.find(35267)))
    print("-335267 is in the set: {}".format(int_set.find(-335267)))
    # Delete does not "downgrading" encoding in Redis
    int_set.delete(0)
    int_set.delete(30)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.delete(-2447483747)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.delete(2447483647)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.synthesize(0)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.synthesize(3)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    int_set.synthesize(4)
    print("{set} ({bytes} bytes)".format(set=int_set, bytes=len(int_set._contents)))
    for i in range(len(int_set)):
        value = int_set.__getitem__(i, int_set._encoding)
        print("{value} is synthesized: {synthesized}".format(value=value,
                                                             synthesized=value.synthesized))


if __name__ == "__main__":
    bst_test()
    hash_table_test()
    sorted_list_test()
    min_heap_test()
    int_set_test()

