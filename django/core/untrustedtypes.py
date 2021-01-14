"""
Subclass builtins classes
"""
from collections import UserString


class UntrustedMixin(object):
    """A Mixin class for adding the Untrusted feature to other classes."""
    def __init__(self, synthesized=False, *args, **kwargs):
        """A synthesized flag to id if a value is synthesized."""
        # Forwards all unused arguments to other base classes down the MRO line.
        self._synthesized = synthesized
        super().__init__(*args, **kwargs)

    @property
    def synthesized(self):
        return self._synthesized

    @synthesized.setter
    def synthesized(self, synthesized):
        self._synthesized = synthesized


class UntrustedInt(UntrustedMixin, int):
    """Subclass Python builtin int class and Untrusted Mixin."""
    def __new__(cls, x, *args, synthesized=False, **kargs):
        self = super().__new__(cls, x, *args, **kargs)
        return self

    def __init__(self, *args, synthesized=False, **kargs):
        super().__init__(synthesized)

    def __add__(self, value):
        """Add (+) method. Note that:
        * UntrustedInt + UntrustedInt -> UntrustedInt
        * UntrustedInt + int -> UntrustedInt
        Use reverse add (__radd__) for:
        * int + UntrustedInt -> UntrustedInt."""
        res = super().__add__(value)
        # result is synthesized if at least one operand is synthesized
        if value.__class__ is type(self):
            synthesized = self.synthesized or value.synthesized
        else:
            synthesized = self.synthesized
        return self.__class__(res, synthesized=synthesized)

    __radd__ = __add__

    def __sub__(self, value):
        """Subtract (-) method."""
        res = super().__sub__(value)
        if value.__class__ is type(self):
            synthesized = self.synthesized or value.synthesized
        else:
            synthesized = self.synthesized
        return self.__class__(res, synthesized=synthesized)

    __rsub__ = __sub__

    def __str__(self):
        return "{value}".format(value=super().__str__())

    # TODO: Adding additional information like "type" breaks z3,
    #  so we don't overwrite __repr__ until we know why it breaks.
    #  Same for other Untrusted classes!
    # def __repr__(self):
    #     return "{type}({value})".format(type=type(self).__name__, value=super().__repr__())


class UntrustedStr(UntrustedMixin, UserString):
    """Subclass collections module's UserString to create
    a custom str class that behaves like Python's built-in
    str but allows further customization. Use UntrustedMixin
    to add the untrusted feature for the class."""
    def __init__(self, seq, synthesized=False):
        super().__init__(synthesized, seq)

    @staticmethod
    def default_hash(input_bytes):
        """Default hash function if no hash
        function is provided by the user."""
        h = 0
        for byte in input_bytes:
            h = h * 31 + byte
        return h

    custom_hash = default_hash

    @classmethod
    def set_hash(cls, new_hash_func):
        """Allows a developer to provide a custom hash
        function. The hash function must take a list of
        bytes and returns an integer; each byte should
        represent one character in string (in ASCII)."""
        cls.custom_hash = new_hash_func

    def __add__(self, other):
        """Add (+) method. Note that:
        * UntrustedStr + UntrustedStr -> UntrustedStr
        * UntrustedStr + str -> UntrustedStr
        Use reverse add (__radd__) for:
        * str + UntrustedStr -> UntrustedStr.
        """
        if isinstance(other, UntrustedStr):
            synthesized = self.synthesized or other.synthesized
            return self.__class__(self.data + other.data, synthesized)
        elif isinstance(other, str):
            return self.__class__(self.data + other, self.synthesized)
        return self.__class__(self.data + str(other), self.synthesized)

    def __radd__(self, other):
        if isinstance(other, str):
            return self.__class__(other + self.data, self.synthesized)
        return self.__class__(str(other) + self.data, self.synthesized)

    def __hash__(self):
        """Override UserStr hash function to use either
        the default or the user-provided hash function."""
        chars = bytes(self.data, 'ascii')
        return type(self).custom_hash(chars)

    def __eq__(self, string):
        """Override to include the synthesized flag into comparison.
        Equality fails if either string is synthesized, regardless of data."""
        if isinstance(string, UntrustedStr):
            return self.data == string.data and not self.synthesized and not string.synthesized
        return self.data == string and not self.synthesized


if __name__ == "__main__":
    # Test int
    base_int = int("A", base=16)
    int_literal = 5
    untrusted_int_1 = UntrustedInt(15)
    untrusted_int_2 = UntrustedInt("B", base=16)
    synthesized_int_1 = UntrustedInt(12, synthesized=True)
    # Some expected test cases
    untrusted_int_3 = untrusted_int_1 + untrusted_int_2
    assert untrusted_int_3 == 26, "untrusted_int_3 should be 26, but it is {}.".format(untrusted_int_3)
    assert untrusted_int_3.synthesized is False, "untrusted_int_3 should not be synthesized."
    assert type(untrusted_int_3) == type(untrusted_int_1), "untrusted_int_3 type is not UntrustedInt"

    untrusted_int_4 = untrusted_int_1 + base_int
    assert untrusted_int_4 == 25, "untrusted_int_4 should be 25, but it is {}.".format(untrusted_int_4)
    assert untrusted_int_4.synthesized is False, "untrusted_int_4 should not be synthesized."
    assert type(untrusted_int_4) == type(untrusted_int_1), "untrusted_int_4 type is not UntrustedInt"

    untrusted_int_5 = untrusted_int_1 + int_literal
    assert untrusted_int_5 == 20, "untrusted_int_5 should be 20, but it is {}.".format(untrusted_int_5)
    assert untrusted_int_5.synthesized is False, "untrusted_int_5 should not be synthesized."
    assert type(untrusted_int_5) == type(untrusted_int_1), "untrusted_int_5 type is not UntrustedInt"

    synthesized_int_2 = synthesized_int_1 + untrusted_int_1
    assert synthesized_int_2 == 27, "synthesized_int_2 should be 27, but it is {}.".format(synthesized_int_2)
    assert synthesized_int_2.synthesized is True, "synthesized_int_2 should be synthesized."
    assert type(synthesized_int_2) == type(synthesized_int_1), "synthesized_int_2 type is not UntrustedInt"

    synthesized_int_3 = synthesized_int_1 + int_literal
    assert synthesized_int_3 == 17, "synthesized_int_3 should be 17, but it is {}.".format(synthesized_int_3)
    assert synthesized_int_3.synthesized is True, "synthesized_int_3 should be synthesized."
    assert type(synthesized_int_3) == type(synthesized_int_1), "synthesized_int_3 type is not UntrustedInt"

    synthesized_int_4 = synthesized_int_1 + base_int
    assert synthesized_int_4 == 22, "synthesized_int_4 should be 22, but it is {}.".format(synthesized_int_4)
    assert synthesized_int_4.synthesized is True, "synthesized_int_4 should be synthesized."
    assert type(synthesized_int_4) == type(synthesized_int_1), "synthesized_int_4 type is not UntrustedInt"

    untrusted_int_6 = base_int + untrusted_int_1
    assert untrusted_int_6 == 25, "untrusted_int_6 should be 25, but it is {}.".format(untrusted_int_6)
    assert untrusted_int_6.synthesized is False, "untrusted_int_6 should not be synthesized."
    assert type(untrusted_int_6) == type(untrusted_int_6), "untrusted_int_6 type is not UntrustedInt"

    untrusted_int_7 = int_literal + untrusted_int_1
    assert untrusted_int_7 == 20, "untrusted_int_7 should be 20, but it is {}.".format(untrusted_int_7)
    assert untrusted_int_7.synthesized is False, "untrusted_int_7 should not be synthesized."
    assert type(untrusted_int_7) == type(untrusted_int_7), "untrusted_int_7 type is not UntrustedInt"

    # Test str
    base_str = str("Hello ")
    str_literal = "World!"
    untrusted_str = UntrustedStr("Untrusted World!")
    synthesized_str = UntrustedStr("Fake World!", synthesized=True)
    # # Some expected test cases
    untrusted_str_1 = untrusted_str + base_str
    assert untrusted_str_1 == "Untrusted World!Hello ", "untrusted_str_1 should be 'Untrusted World!Hello'," \
                                                        " but it is {}.".format(untrusted_str_1)
    assert untrusted_str_1.synthesized is False, "untrusted_str_1 should not be synthesized."
    assert type(untrusted_str_1) == type(untrusted_str), "untrusted_str_1 type is not UntrustedStr"

    untrusted_str_2 = untrusted_str + str_literal
    assert untrusted_str_2 == "Untrusted World!World!", "untrusted_str_2 should be 'Untrusted World!World!'," \
                                                        " but it is {}.".format(untrusted_str_2)
    assert untrusted_str_2.synthesized is False, "untrusted_str_2 should not be synthesized."
    assert type(untrusted_str_2) == type(untrusted_str), "untrusted_str_2 type is not UntrustedStr"

    synthesized_str_1 = synthesized_str + base_str
    assert synthesized_str_1 == "Fake World!Hello ", "synthesized_str_1 should be 'Fake World!Hello'," \
                                                     " but it is {}.".format(synthesized_str_1)
    assert synthesized_str_1.synthesized is True, "synthesized_str_1 should be synthesized."
    assert type(synthesized_str_1) == type(untrusted_str), "synthesized_str_1 type is not UntrustedStr"

    synthesized_str_2 = synthesized_str + str_literal
    assert synthesized_str_2 == "Fake World!World!", "synthesized_str_2 should be 'Fake World!World!'," \
                                                     " but it is {}.".format(synthesized_str_2)
    assert synthesized_str_2.synthesized is True, "synthesized_str_2 should be synthesized."
    assert type(synthesized_str_2) == type(untrusted_str), "synthesized_str_2 type is not UntrustedStr"

    untrusted_str_3 = base_str + untrusted_str
    assert untrusted_str_3 == "Hello Untrusted World!", "untrusted_str_3 should be 'Hello Untrusted World!'," \
                                                        " but it is {}.".format(untrusted_str_3)
    assert untrusted_str_3.synthesized is False, "untrusted_str_3 should not be synthesized."
    assert type(untrusted_str_3) == type(untrusted_str), "untrusted_str_3 type is not UntrustedStr"

    synthesized_str_3 = base_str + synthesized_str
    assert synthesized_str_3 == "Hello Fake World!", "synthesized_str_3 should be 'Hello Fake World'," \
                                                     " but it is {}.".format(synthesized_str_3)
    assert synthesized_str_3.synthesized is True, "synthesized_str_3 should be synthesized."
    assert type(synthesized_str_3) == type(untrusted_str), "synthesized_str_3 type is not UntrustedStr"

    synthesized_str_4 = str_literal + synthesized_str
    assert synthesized_str_4 == "World!Fake World!", "synthesized_str_4 should be 'World!Fake World'," \
                                                     " but it is {}.".format(synthesized_str_4)
    assert synthesized_str_4.synthesized is True, "synthesized_str_4 should be synthesized."
    assert type(synthesized_str_4) == type(untrusted_str), "synthesized_str_4 type is not UntrustedStr"

