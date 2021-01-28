"""Binary search tree and synthesizable BST."""

from django.splice.synthesis import init_synthesizer


class BiNode(object):
    """Node class with two children and a parent."""
    def __init__(self, key, val):
        self._key = key
        self._val = val
        self._left = None
        self._right = None
        self._parent = None

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, val):
        self._val = val

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

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, node):
        self._parent = node


class BinarySearchTree(object):
    """BST using BiNode."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = None

    def insert(self, key, val):
        """
        Insert a key/value pair to a BST and returns False if
        insertion failed. This is the public API to construct
        a new tree or add a new node to an existing tree.
        """
        if self.root is None:
            self._set_root(key, val)
            return True
        else:
            return self._insert_node(self.root, key, val)

    def _set_root(self, key, val):
        """
        A helper function to set the root node. Users should not call
        this function directly but call the public API insert() to
        construct a new tree instead.
        """
        self.root = BiNode(key, val)

    def _insert_node(self, curr, key, val):
        """
        Only unique keys modify the tree after insertion. If insertion is
        not successful (e.g., 'key' is already in the tree), it returns
        False. Users should not call this function directly but call the
        public API insert() to add a new node to an existing tree.
        """
        if key < curr.key:
            if curr.left_child:
                return self._insert_node(curr.left_child, key, val)
            else:
                curr.left_child = BiNode(key, val)
                curr.left_child.parent = curr
                return True
        elif key > curr.key:
            if curr.right_child:
                return self._insert_node(curr.right_child, key, val)
            else:
                curr.right_child = BiNode(key, val)
                curr.right_child.parent = curr
                return True
        else:
            return False

    def get(self, key):
        """Returns the value for a given key if the key exists. Otherwise, return None."""
        n = self.find(key)
        if not n:
            return None
        return n.val

    def find(self, key):
        """
        Return the node if key is in the tree; otherwise, return None.
        This is the public API to find a node of a given key in a tree.
        """
        return self._find_node(self.root, key)

    def _find_node(self, curr, key):
        """
        A helper function to find a node based on the given key.
        Return None if the key does not exist in the tree. Users
        should not call this method but the public API find().
        """
        if not curr:
            return None

        if key == curr.key:
            return curr
        elif key > curr.key:
            return self._find_node(curr.right_child, key)
        else:
            return self._find_node(curr.left_child, key)

    def delete(self, key):
        """
        Modify the tree by removing a node if it has the given
        key. Otherwise, do nothing. This is the public API to
        delete a node in a tree.
        """
        self.root = self._delete_node(self.root, key)

    def _delete_node(self, curr, key):
        """
        Find a node based on the given key and delete the node
        from the tree if it exists. Users should not call this
        helper function but the public API delete() instead.
        """
        if curr is None:
            return curr

        if key < curr.key:
            curr.left_child = self._delete_node(curr.left_child, key)
        elif key > curr.key:
            curr.right_child = self._delete_node(curr.right_child, key)
        else:
            if curr.left_child is None:
                if curr.right_child is not None:
                    curr.right_child.parent = curr.parent
                return curr.right_child
            elif curr.right_child is None:
                if curr.left_child is not None:
                    curr.left_child.parent = curr.parent
                return curr.left_child
            candidate = self._min_value_node(curr.right_child)
            curr.key = candidate.key
            curr.val = candidate.val
            curr.right_child = self._delete_node(curr.right_child, candidate.key)
        return curr

    def _max_value_node(self, node):
        """
        Return the node with the maximum key in a
        (sub)tree rooted at node. The maximum value
        is the node itself if it has no right subtree.
        """
        if node is None:
            return node
        if node.right_child:
            return self._max_value_node(node.right_child)
        return node

    def _max_value(self, node):
        """
        Return the maximum key in a (sub)tree rooted at node.
        The maximum value is the node itself if it has no
        right subtree. Return False if the node does not exist.
        """
        max_node = self._max_value_node(node)
        if max_node is None:
            return False
        return max_node.key

    def _min_value_node(self, node):
        """
        Return the node with the minimum key in a
        (sub)tree rooted at node. The minimum value
        is the node itself if it has no left subtree.
        """
        if node is None:
            return node
        if node.left_child:
            return self._min_value_node(node.left_child)
        else:
            return node

    def _min_value(self, node):
        """
        Return the minimum key in a (sub)tree rooted at node.
        The minimum value is the node itself if it has no
        left subtree. Return False if the node does not exist.
        """
        min_node = self._min_value_node(node)
        if min_node is None:
            return False
        return min_node.key

    def to_ordered_list(self, node, ordered_list):
        """
        Convert the tree into an in-ordered list of nodes. The list is stored in 'ordered_list'."""
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
        printout = str()
        for node in ordered_list:
            if node.key:
                printout += "{key}({value}) ".format(key=node.key, value=node.val)
            else:
                printout += "{value} ".format(value=node.val)
        return printout


class SynthesizableBST(BinarySearchTree):
    """The synthesizable version of binary search tree."""
    def synthesize(self, key_or_val):
        """Synthesize the val (or key if exists) of a node.
        Only performs bounded value synthesis if both upper
        and lower bound exist for the node. Otherwise, create
        an Untrusted val (or key if exists) of the same value
        and with the synthesized flag set. If synthesis
        failed for any reason, return False. If synthesis
        succeeded, return True."""
        node = self.find(key_or_val)
        if node is None:
            return False
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
