"""
Subclass builtins classes
"""


class Untrusted(object):
    """Base class for any Untrusted data types."""
    def __init__(self, synthesized=False):
        """A synthesized flag to id if a value is synthesized."""
        self._synthesized = synthesized

    @property
    def synthesized(self):
        return self._synthesized

    @synthesized.setter
    def synthesized(self, synthesized):
        self._synthesized = synthesized


class UntrustedInt(int, Untrusted):
    """Subclass Python builtin int class and Untrusted base class."""
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


class UntrustedStr(str, Untrusted):
    """Subclass Python builtin str class and Untrusted base class."""
    def __new__(cls, *args, synthesized=False, **kargs):
        self = super().__new__(cls, *args, **kargs)
        return self

    def __init__(self, *args, synthesized=False, **kargs):
        super().__init__(synthesized)

    # TODO: While overwriting __getattribute__ returns UntrustedStr
    #  type, the following code does not change untrusted and synthesized
    #  attributes. For example, calling:
    #  untrusted_str_3 = untrusted_str_1.__add__(untrusted_str_2) does
    #  not change untrusted_str_3.synthesized to True if either one of
    #  the variable on the RHS has a synthesized attribute equal to True.
    #  This is not an expected behavior (c.f. if we individually overwrite
    #  the __add__ method, we can set the synthesized attribute ourselves.)
    # def __getattribute__(self, name):
    #     """Overwrite base class str __getattribute__ so that methods on UntrustedStr
    #     returns UntrustedStr instead of str. Note that operators like + does not invoke
    #     __getattribute__ so they don't get overwritten! """
    #     # dir(str) gets a list of attributes of str
    #     if name in dir(str):
    #
    #         def method(self, *args, **kwargs):
    #             # getattr() gets an attribute of a class/instance
    #             # (which might trigger __getattribute__ and/or __getattr__)
    #             value = getattr(super(), name)(*args, **kwargs)
    #             # Not every str method returns a str, but
    #             # Only str needs to be casted to UntrustedStr
    #             if isinstance(value, str):
    #                 return type(self)(value)
    #             elif isinstance(value, list):
    #                 return [type(self)(i) for i in value]
    #             elif isinstance(value, tuple):
    #                 return tuple(type(self)(i) for i in value)
    #             # Methods that return types like dict, bool, or int
    #             else:
    #                 return value
    #
    #         return method.__get__(self)
    #     # Delegate the call to parent class, i.e., str
    #     else:
    #         return super().__getattribute__(name)

    def __add__(self, value):
        """Add (+) method. Note that:
        * UntrustedStr + UntrustedStr -> UntrustedStr
        * UntrustedStr + str -> UntrustedStr
        """
        # TODO: str + UntrustedStr -> str. Note that we
        #  cannot use __radd__ like in UntrustedInt since
        #  string addition is not commutative!

        res = super().__add__(value)
        # result is synthesized if at least one operand is synthesized
        if value.__class__ is type(self):
            synthesized = self.synthesized or value.synthesized
        else:
            synthesized = self.synthesized
        return self.__class__(res, synthesized=synthesized)

    def __str__(self):
        return "{value}".format(value=super().__str__())

    # def __repr__(self):
    #     return "{type}({value})".format(type=type(self).__name__, value=super().__repr__())


if __name__ == "__main__":
    base_int = int("A", base=16)
    int_literal = 5
    untrusted_int_1 = UntrustedInt(15)
    untrusted_int_2 = UntrustedInt("B", base=16)
    synthesized_int_1 = UntrustedInt(12, synthesized=True)
    # Some expected test cases
    untrusted_int_3 = untrusted_int_1 + untrusted_int_2
    assert untrusted_int_3 == 26, "untrusted_int_3 should be 26, but it is {}.".format(untrusted_int_3)
    assert untrusted_int_3.synthesized is False, "untrusted_int_3 should not be synthesized."
    untrusted_int_4 = untrusted_int_1 + base_int
    assert untrusted_int_4 == 25, "untrusted_int_4 should be 25, but it is {}.".format(untrusted_int_4)
    assert untrusted_int_4.synthesized is False, "untrusted_int_4 should not be synthesized."
    untrusted_int_5 = untrusted_int_1 + int_literal
    assert untrusted_int_5 == 20, "untrusted_int_5 should be 20, but it is {}.".format(untrusted_int_5)
    assert untrusted_int_5.synthesized is False, "untrusted_int_5 should not be synthesized."
    synthesized_int_2 = synthesized_int_1 + untrusted_int_1
    assert synthesized_int_2 == 27, "synthesized_int_2 should be 27, but it is {}.".format(synthesized_int_2)
    assert synthesized_int_2.synthesized is True, "synthesized_int_2 should be synthesized."
    synthesized_int_3 = synthesized_int_1 + int_literal
    assert synthesized_int_3 == 17, "synthesized_int_3 should be 17, but it is {}.".format(synthesized_int_3)
    assert synthesized_int_3.synthesized is True, "synthesized_int_3 should be synthesized."
    synthesized_int_4 = synthesized_int_1 + base_int
    assert synthesized_int_4 == 22, "synthesized_int_4 should be 22, but it is {}.".format(synthesized_int_4)
    assert synthesized_int_4.synthesized is True, "synthesized_int_4 should be synthesized."
    untrusted_int_6 = base_int + untrusted_int_1
    assert untrusted_int_6 == 25, "untrusted_int_6 should be 25, but it is {}.".format(untrusted_int_6)
    assert untrusted_int_6.synthesized is False, "untrusted_int_6 should not be synthesized."

    base_str = str("Hello ")
    str_literal = "World!"
    untrusted_str = UntrustedStr("Untrusted World!")
    synthesized_str = UntrustedStr("Fake World!", synthesized=True)
    # Some expected test cases
    untrusted_str_1 = untrusted_str + base_str
    assert untrusted_str_1 == "Untrusted World!Hello ", "untrusted_str_1 should be 'Untrusted World!Hello'," \
                                                        " but it is {}.".format(untrusted_str_1)
    assert untrusted_str_1.synthesized is False, "untrusted_str_1 should not be synthesized."
    untrusted_str_2 = untrusted_str + str_literal
    assert untrusted_str_2 == "Untrusted World!World!", "untrusted_str_2 should be 'Untrusted World!World!'," \
                                                        " but it is {}.".format(untrusted_str_2)
    assert untrusted_str_2.synthesized is False, "untrusted_str_2 should not be synthesized."
    synthesized_str_1 = synthesized_str + base_str
    assert synthesized_str_1 == "Fake World!Hello ", "synthesized_str_1 should be 'Fake World!Hello'," \
                                                     " but it is {}.".format(synthesized_str_1)
    assert synthesized_str_1.synthesized is True, "synthesized_str_1 should be synthesized."
    synthesized_str_2 = synthesized_str + str_literal
    assert synthesized_str_2 == "Fake World!World!", "synthesized_str_2 should be 'Fake World!World!'," \
                                                     " but it is {}.".format(synthesized_str_2)
    assert synthesized_str_2.synthesized is True, "synthesized_str_2 should be synthesized."
    untrusted_str_2 = base_str + untrusted_str
    assert untrusted_str_2 == "Hello Untrusted World!", "untrusted_str_2 should be 'Hello Untrusted World!'," \
                                                        " but it is {}.".format(untrusted_str_2)
    # TODO: fix the sad case if possible
    base_str_1 = base_str + untrusted_str
    print("({base_str_type})'{base_str_value}' + ({untrusted_str_type})'{untrusted_str_value}' "
          "= ({result_type})'{result_value}'".format(base_str_type=base_str.__class__,
                                                     base_str_value=base_str,
                                                     untrusted_str_type=untrusted_str.__class__,
                                                     untrusted_str_value=untrusted_str,
                                                     result_type=base_str_1.__class__,
                                                     result_value=base_str_1))
    base_str_2 = base_str + synthesized_str
    print("({base_str_type})'{base_str_value}' + ({synthesized_str_type})'{synthesized_str_value}' "
          "= ({result_type})'{result_value}'".format(base_str_type=base_str.__class__,
                                                     base_str_value=base_str,
                                                     synthesized_str_type=synthesized_str.__class__,
                                                     synthesized_str_value=synthesized_str,
                                                     result_type=base_str_1.__class__,
                                                     result_value=base_str_1))
