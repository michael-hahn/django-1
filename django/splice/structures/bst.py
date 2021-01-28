"""Binary search tree and synthesizable BST"""
from django.splice.synthesis import init_synthesizer


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = None

    def insert(self, val, key=None):
        """Insert a value (or key/value pair if keys are used) to a BST.
        Returns False if insertion failed (e.g., if a key/value pair
        is given to be inserted into a value-only tree). This is the
        public API to construct a new tree or add new nodes to an existing tree."""
        if self.root is None:
            self._set_root(val, key)
            return True
        else:
            # BST nodes either all have a key or none of the nodes have a key!
            if self.root.has_key() and not key:
                return False
            elif not self.root.has_key() and key:
                return False
            else:
                return self._insert_node(self.root, val, key)

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
                return self._insert_node(curr.left_child, val, key)
            else:
                curr.left_child = BiNode(val, key=key)
                return True
        elif key and key > curr.key or not key and val > curr.val:
            if curr.right_child:
                return self._insert_node(curr.right_child, val, key)
            else:
                curr.right_child = BiNode(val, key=key)
                return True
        else:
            return False

    def get(self, key):
        """If the BST has both a key and a value in a node,
        returns the value for a given key if the key exists.
        Otherwise, return None."""
        n = self.find(key)
        if not n:
            return None
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


class SynthesizableBST(BinarySearchTree):
    """The synthesizable version of binary search tree."""
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
                # The val will have its synthesized flag set
                node.val.synthesized = True
            else:
                node.val = synthesized_value
        return True


if __name__ == "__main__":
    pass
