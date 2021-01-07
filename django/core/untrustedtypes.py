"""
Subclass builtins classes
"""


class UntrustedInt(int):
    """Subclass Python builtin int class with Splice specific attributes."""
    def __new__(cls, x, *args, untrusted=True, synthesized=False, **kargs):
        self = super().__new__(cls, x, *args, **kargs)
        self.untrusted = untrusted
        self.synthesized = synthesized
        return self

    def is_untrusted(self):
        return self.untrusted

    def is_synthesized(self):
        return self.synthesized

    def __add__(self, value):
        res = super().__add__(value)
        # result is untrusted if at least one operand is untrusted
        untrusted = self.untrusted or value.untrusted
        # result is synthesized if at least one operand is synthesized
        synthesized = self.synthesized or value.synthesized
        return self.__class__(res, untrusted=untrusted, synthesized=synthesized)

    def __sub__(self, value):
        res = super().__sub__(value)
        untrusted = self.untrusted or value.untrusted
        synthesized = self.synthesized or value.synthesized
        return self.__class__(res, untrusted=untrusted, synthesized=synthesized)

    def __str__(self):
        return "{value}".format(value=super().__str__())

    # TODO: Adding additional information like "type" breaks z3,
    #  so we don't overwrite __repr__ until we know why it breaks.
    #  Same for other Untrusted classes!
    # def __repr__(self):
    #     return "{type}({value})".format(type=type(self).__name__, value=super().__repr__())


class UntrustedStr(str):
    """Subclass Python builtin str class with Splice specific attributes."""
    def __new__(cls, *args, untrusted=True, synthesized=False, **kargs):
        self = super().__new__(cls, *args, **kargs)
        self.untrusted = untrusted
        self.synthesized = synthesized
        return self

    def is_untrusted(self):
        return self.untrusted

    def is_synthesized(self):
        return self.synthesized

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
        res = super().__add__(value)
        untrusted = self.untrusted or value.untrusted
        synthesized = self.synthesized or value.synthesized
        # Do not use self.__class__() if __getattribute__ above is defined
        # because __class__ will trigger __getattribute__
        return self.__class__(res, untrusted=untrusted, synthesized=synthesized)

    def __str__(self):
        return "{value}".format(value=super().__str__())

    # def __repr__(self):
    #     return "{type}({value})".format(type=type(self).__name__, value=super().__repr__())


if __name__ == "__main__":
    str_1 = UntrustedStr("Hello ")
    str_2 = UntrustedStr("World!")
    str_2.synthesized = True
    print("str_2 synthesized:{}".format(str_2.is_synthesized()))
    str_3 = str_1 + str_2
    print("str_3 type:{}".format(type(str_3)))
    str_4 = str_1.__add__(str_2)
    print("str_4: {}".format(str_4))
    print("str_4 type:{}".format(type(str_4)))
    print("str_4 synthesized:{}".format(str_4.is_synthesized()))
