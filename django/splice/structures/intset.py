"""Redis IntSet and Synthesizable IntSet."""

from django.splice.synthesis import init_synthesizer
from django.splice.splicetypes import SpliceInt


class IntSet(object):
    """
    Python implementation of Redis' intSet data structure (simplified).
    A quick introduction can be found here:
    http://blog.wjin.org/posts/redis-internal-data-structure-intset.html
    Original C code reference (v5.0.0) can be found here:
    http://blog.wjin.org/posts/redis-internal-data-structure-intset.html.
    Unlike the original implementation, we will always use big endian.
    """
    # Different encodings use different numbers of bytes
    INTSET_ENC_INT16 = 2
    INTSET_ENC_INT32 = 4
    INTSET_ENC_INT64 = 8
    # Min/max integer value for different encodings
    INT16_MIN = -32768
    INT16_MAX = 32767
    INT32_MIN = -2_147_483_648
    INT32_MAX = 2_147_483_647

    def __init__(self, *args, **kwargs):
        """
        Initialize an intSet with default int16 encoding, which
        can be upgraded to int32 and then int64 later if needed.
        self._length is the number of actual integers in intSet, *not*
        the length of self._contents. Each element in self._contents
        is an int8 value.
        """
        super().__init__(*args, **kwargs)
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
        """
        Return the value at pos, using the configured encoding.
        Note that pos is in terms of the set visible to the user,
        it is not the location in self._contents (i.e., pos would
        correspond to self._length).
        """
        return int.from_bytes(self._contents[pos*encoding:(pos+1)*encoding], byteorder='big', signed=True)

    def get(self, pos):
        """
        Return the value at pos. Unlike __getitem__, this is a public
        API so that users do not need to worry about the encoding.
        """
        return self.__getitem__(pos, self._encoding)

    def __setitem__(self, pos, value, encoding):
        """
        Set the value at pos using the configured encoding.
        Note that pos is in terms of the set visible to the user,
        it is not the location in self._contents (i.e., pos would
        correspond to self._length).
        """
        byte_arr = [int(i) for i in value.to_bytes(self._encoding, byteorder='big', signed=True)]
        for i in range(pos*encoding, (pos+1)*encoding):
            self._contents[i] = byte_arr[i-pos*encoding]

    def __len__(self):
        """Return the number of elements in the intSet."""
        return self._length

    def _search(self, value):
        """
        Search for the position of "value". Returns a tuple (1, pos)
        if the value was found and pos would be the position of the value
        within the intSet (note that values are sorted); otherwise, return
        (0, pos) if the value is not present in the intSet and pos is
        the position where value can be inserted.
        """
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
        """
        Move elements starting from from_pos position to
        locations starting from to_pos position in intSet.
        """
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

    def __iter__(self):
        """Iterate through the intSet."""
        for i in range(self._length):
            yield self.get(i)

    def __str__(self):
        """The contents of intSet."""
        set_str = "[ "
        for i in range(self._length):
            set_str += str(self.__getitem__(i, self._encoding)) + " "
        set_str += "]"
        return set_str


class SynthesizableIntSet(IntSet):
    """
    Inherit from IntSet to create a custom IntSet that
    behaves exactly like a IntSet (with elements sorted
    in the list) but the elements in the SynthesizableIntSet
    can be synthesized. We intentionally did not add
    the synthesis feature in the IntSet superclass (even
    though we implemented it ourselves) because we want to
    highlight the changes that must be done to make IntSet
    synthesizable (and that its unique encoding design
    makes synthesis different from, e.g., a sorted list).
    """
    def __getitem__(self, pos, encoding):
        """
        Override IntSet's __getitem__ method because
        we must return a SpliceInt instead of int
        and we must check if the returned value should
        have synthesized flag set or not.
        """
        # All values in self._contents should be of type SpliceInt
        # If any value is synthesized, the entire value should be synthesized
        synthesized = False
        for i in range(pos*encoding, (pos+1)*encoding):
            synthesized = synthesized or self._contents[i].synthesized
        return SpliceInt(int.from_bytes(self._contents[pos*encoding:(pos+1)*encoding],
                                        byteorder='big', signed=True),
                         trusted=False,
                         synthesized=synthesized)

    def __setitem__(self, pos, value, encoding):
        """
        Override IntSet's __setitem__ method
        because value is converted into a byte
        array to be inserted into the data
        structure, instead of being directly
        inserted into the data structure. We do
        not want to "lose" the Untrusted type
        during the conversion.
        """
        synthesized = value.synthesized
        byte_arr = [SpliceInt(i, trusted=False, synthesized=synthesized)
                    for i in value.to_bytes(self._encoding, byteorder='big', signed=True)]
        for i in range(pos*encoding, (pos+1)*encoding):
            self._contents[i] = byte_arr[i-pos*encoding]

    def synthesize(self, pos):
        """
        Synthesize a new value at pos (of intSet) without invalidating ordered-set
        invariant. The synthesized value must be smaller than the next value (if exist)
        and larger than the previous one (if exists). Return True if synthesis succeeds.
        It is possible that the same value is marked as synthesized because no other
        synthesis value is possible.

        Note: Synthesis should not change the encoding of this data structure. Therefore,
        it is possible that a suitable value only exists in a different encoding but
        because we cannot use the value, we would have to use the same value.
        """
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
        if self._length == 1:
            # No value constraints if it is the only element in intSet
            pass
        elif pos == 0:
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


if __name__ == "__main__":
    pass
