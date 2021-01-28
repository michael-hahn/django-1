"""Synthesizable min heap data structure"""
import heapq

from django.splice.synthesis import init_synthesizer


class SynthesizableMinHeap(object):
    """A binary min heap for which a[k] <= a[2*k+1] and a[k] <= a[2*k+2] for
    all k, counting elements from 0. For the sake of comparison, non-existing
    elements are considered to be infinite.  The interesting property of a
    heap is that a[0] is always its smallest element. See docstring from heapq.py."""
    def __init__(self, initial=None, *args, **kwargs):
        """Defaults to an empty heap. Initial can also be
        a list, which could be transformed into a heap.

        'initial' should not be a mutable default value, because:
        https://stackoverflow.com/a/40750485/9632613."""
        super().__init__(*args, **kwargs)
        if not initial:
            initial = list()
        self._heap = initial
        heapq.heapify(self._heap)

    def add(self, data):
        """Add an item to the heap, while maintaining heap invariant.
        This is the public-facing interface to add data to SynthesizableMinHeap."""
        heapq.heappush(self._heap, data)

    def delete(self):
        """Pop the smallest item off the heap, while maintaining heap invariant.
        BaseSynthesizableStruct enforces implementation of this method. This is
        the public-facing interface to obtain data from SynthesizableMinHeap.

        Important Note: this method should not be used as get() since if it fails
        (because it returns a synthesized value), it would have already modified
        the data structure and popped the head of the queue! A get() function that
        might fail should not modify the data structure unless there is roll-back
        action defined somehow!"""
        return heapq.heappop(self._heap)

    def get(self):
        """Return the smallest item from the heap (if exists),
        without popping it out. Otherwise, return None."""
        if len(self._heap) > 0:
            return self._heap[0]
        return None

    def clear(self):
        self._heap.clear()

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
                heap += "[{parent} (Synthesized: {parent_synthesis})] " \
                        "-> [{left} (Synthesized: {left_synthesis})  " \
                        "{right} (Synthesized: " \
                        "{right_synthesis})]\n".format(parent=self._heap[i],
                                                       parent_synthesis=self._heap[i].synthesized,
                                                       left=self._heap[2*i+1],
                                                       left_synthesis=self._heap[2*i+1].synthesized,
                                                       right=self._heap[2*i+2],
                                                       right_synthesis=self._heap[2*i+2].synthesized)
            else:
                heap += "[{parent} (Synthesized: {parent_synthesis})] " \
                        "-> [{left} (Synthesized: " \
                        "{left_synthesis})]".format(parent=self._heap[i],
                                                    parent_synthesis=self._heap[i].synthesized,
                                                    left=self._heap[2 * i + 1],
                                                    left_synthesis=self._heap[2 * i + 1].synthesized)
        return heap


if __name__ == "__main__":
    pass
