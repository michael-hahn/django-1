"""
Untrusted classes
"""
from collections import UserString


def add_synthesis(func):
    """A function decorator that decorates func.
    This decorator makes an UntrustedX class inherit
    all its base (non-untrusted) class functions
    and return Untrusted values."""
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res is NotImplemented:
            return res
        # Set synthesized flag if any args/kwargs sets the flag
        synthesized = False
        for arg in args:
            if issubclass(type(arg), UntrustedMixin):
                synthesized = synthesized or arg.synthesized
        for key, value in kwargs.items():
            if issubclass(type(value), UntrustedMixin):
                synthesized = synthesized or value.synthesized

        if isinstance(res, UntrustedMixin):
            # If res is already an Untrusted type (e.g., in UserStr inheritance uses
            # self.__class__() to create UntrustedStr instead of UserStr or str
            # class objects, but synthesized flag might not be set correctly!
            res.synthesized = synthesized
            return res
        # boolean value is always bool (bool is not extensible)
        # bool is a subclass of int, so we must check this first
        elif isinstance(res, bool):
            return res
        elif isinstance(res, int):
            return UntrustedInt(res, synthesized=synthesized)
        elif isinstance(res, float):
            return UntrustedFloat(res, synthesized=synthesized)
        elif isinstance(res, str) or isinstance(res, UserString):
            return UntrustedStr(res, synthesized=synthesized)
        #####################################################
        # TODO: Add more casting here for new untrusted types
        #####################################################
        # TODO: We may consider a generic Untrusted type,
        #  instead of returning a trusted value.
        else:
            return res

    return wrapper


def add_synthesis_to_func(cls):
    """A class decorator that decorates all functions in cls
    so that they are synthesis-aware. If cls is a subclass of
    some base classes, then we want functions in base class to be
    synthesis-aware as well.

    Important note: Any cls (UntrustedX) function to be decorated must
    start with either "synthesis_" or "_synthesis_" (for protected
    methods), while base class functions have no such restriction
    (since it is likely that developers have no control over the
    base class). Using this convention, developers can prevent
    base class functions from being decorated by overriding the
    function (and just calling base class function). If, for example,
    the developer needs to override a dunder function, and the
    overridden function needs to be decorated, they should first
    implement a helper function '_synthesize__dunder__' and then
    call the helper function in the dunder function. As such,
    _synthesize__dunder__ will be decorated (and therefore the
    calling dunder function)."""
    # set of function names already been decorated/inspected
    handled_funcs = set()
    # First handle all functions in cls class
    for key, value in cls.__dict__.items():
        # Only callable functions are decorated
        if not callable(value):
            continue
        # All callable functions are inspected in cls
        handled_funcs.add(key)
        if key.startswith("synthesis_") or key.startswith("_synthesis_"):
            setattr(cls, key, add_synthesis(value))
    # Handle base class functions if exists. Base classes are
    # unlikely to follow our synthesis naming convention.
    # However, some dunder methods clearly should *not* be
    # decorated, we will add them in handled_funcs.
    # Some can be more subtle:
    # * __int__: This dunder method is called during int().
    #            If int() is called, we should not decorate it
    #            but actually returns an int typed value.
    handled_funcs.update({'__dict__', '__module__', '__doc__', '__repr__',
                          '__getattribute__', '__str__', '__new__', '__format__',
                          '__int__'})
    # __mro__ defines the list of *ordered* base classes (the first being cls and
    # the second being UntrustedMixin; UntrustedMixin should *not* be decorated)
    for base in cls.__mro__[2:]:
        for key, value in base.__dict__.items():
            # Only callable functions that are not handled by previous classes
            if not callable(value) or key in handled_funcs:
                continue
            # All callable functions are inspected in the current base class
            handled_funcs.add(key)
            # Delegate add_synthesis() to handle other cases
            # since there is not much convention we can specify.
            # Note that it is possible add_synthesis() can just
            # return the same function (value) with no changes.
            setattr(cls, key, add_synthesis(value))
    return cls


class UntrustedMixin(object):
    """A Mixin class for adding the Untrusted feature to other classes.

    Important note: for __init_subclass__'s add_synthesis_to_func() to work
    correct, UntrustedMixin must used as the *first* parent class in a subclass."""
    def __init__(self, synthesized=False, *args, **kwargs):
        """A synthesized flag to id if a value is synthesized."""
        # Forwards all unused arguments to other base classes down the MRO line.
        self._synthesized = synthesized
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        """Whenever a class inherits from this, this function is called on that class,
        so that we can change the behavior of subclasses. This is closely related to
        class decorators, but where class decorators only affect the specific class
        they’re applied to, __init_subclass__ solely applies to future subclasses of
        the class defining the method.

        Here we use both __init_subclass__ and class decorator, so that a subclass
        of UntrustedMixin and its subclasses can be decorated."""
        super().__init_subclass__(**kwargs)
        add_synthesis_to_func(cls)

    @property
    def synthesized(self):
        return self._synthesized

    @synthesized.setter
    def synthesized(self, synthesized):
        self._synthesized = synthesized


class UntrustedInt(UntrustedMixin, int):
    """Subclass Python builtin int class and Untrusted Mixin.
    Note that synthesized is a keyed parameter."""
    def __new__(cls, x, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, x, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @staticmethod
    def default_hash(input_integer):
        """Default hash function if no hash
        function is provided by the user."""
        return input_integer % (2**63 - 1)

    custom_hash = default_hash

    @classmethod
    def set_hash(cls, new_hash_func):
        """Allows a developer to provide a custom hash
        function. The hash function must take an integer
        and returns an integer.

        Hash function must be Z3 friendly."""
        cls.custom_hash = new_hash_func

    def __hash__(self):
        """Override hash function to use either our default
        hash or the user-provided hash function."""
        return type(self).custom_hash(int(self))

    def __str__(self):
        return "{value}".format(value=super().__str__())


class UntrustedFloat(UntrustedMixin, float):
    """Subclass Python builtin float class and Untrusted Mixin.
    Note that synthesized is a keyed parameter."""
    def __new__(cls, x, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, x, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)


class UntrustedStr(UntrustedMixin, UserString):
    """Subclass collections module's UserString to create
    a custom str class that behaves like Python's built-in
    str but allows further customization. Use UntrustedMixin
    to add the untrusted feature for the class."""
    def __init__(self, seq, *, synthesized=False):
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
        represent one character in string (in ASCII).

        Hash function must be Z3 friendly."""
        cls.custom_hash = new_hash_func

    def __hash__(self):
        """Override UserStr hash function to use either
        the default or the user-provided hash function."""
        chars = bytes(self.data, 'ascii')
        return type(self).custom_hash(chars)


def untrusted_int_test():
    base_int = int("A", base=16)
    int_literal = 5
    untrusted_int_1 = UntrustedInt(15)
    untrusted_int_2 = UntrustedInt("B", base=16)
    synthesized_int_1 = UntrustedInt(12, synthesized=True)

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
    assert type(untrusted_int_6) == type(untrusted_int_1), "untrusted_int_6 type is not UntrustedInt"

    untrusted_int_7 = int_literal + untrusted_int_1
    assert untrusted_int_7 == 20, "untrusted_int_7 should be 20, but it is {}.".format(untrusted_int_7)
    assert untrusted_int_7.synthesized is False, "untrusted_int_7 should not be synthesized."
    assert type(untrusted_int_7) == type(untrusted_int_1), "untrusted_int_7 type is not UntrustedInt"

    untrusted_int_8 = untrusted_int_1 - base_int
    assert untrusted_int_8 == 5, "untrusted_int_8 should be 5, but it is {}.".format(untrusted_int_8)
    assert untrusted_int_8.synthesized is False, "untrusted_int_8 should not be synthesized."
    assert type(untrusted_int_8) == type(untrusted_int_1), "untrusted_int_8 type is not UntrustedInt"

    untrusted_int_9 = base_int - untrusted_int_1
    assert untrusted_int_9 == -5, "untrusted_int_9 should be -5, but it is {}.".format(untrusted_int_9)
    assert untrusted_int_9.synthesized is False, "untrusted_int_9 should not be synthesized."
    assert type(untrusted_int_9) == type(untrusted_int_1), "untrusted_int_9 type is not UntrustedInt"

    synthesized_int_5 = int_literal - synthesized_int_1
    assert synthesized_int_5 == -7, "synthesized_int_5 should be -7, but it is {}.".format(synthesized_int_5)
    assert synthesized_int_5.synthesized is True, "synthesized_int_5 should be synthesized."
    assert type(synthesized_int_5) == type(synthesized_int_1), "synthesized_int_5 type is not UntrustedInt"

    synthesized_int_6 = int_literal * synthesized_int_1
    assert synthesized_int_6 == 60, "synthesized_int_6 should be 60, but it is {}.".format(synthesized_int_6)
    assert synthesized_int_6.synthesized is True, "synthesized_int_6 should be synthesized."
    assert type(synthesized_int_6) == type(synthesized_int_1), "synthesized_int_6 type is not UntrustedInt"

    synthesized_int_7 = synthesized_int_1 // int_literal
    assert synthesized_int_7 == 2, "synthesized_int_7 should be 2, but it is {}.".format(synthesized_int_7)
    assert synthesized_int_7.synthesized is True, "synthesized_int_7 should be synthesized."
    assert type(synthesized_int_7) == type(synthesized_int_1), "synthesized_int_7 type is not UntrustedInt"

    synthesized_int_8 = synthesized_int_1 / int_literal
    assert synthesized_int_8 == 2.4, "synthesized_int_8 should be 2.4, but it is {}.".format(synthesized_int_8)
    assert synthesized_int_8.synthesized is True, "synthesized_int_8 should be synthesized."
    assert type(synthesized_int_8) == UntrustedFloat, "synthesized_int_8 type is not UntrustedFloat"

    synthesized_int_9 = int_literal / synthesized_int_1
    assert synthesized_int_9 == 5/12, "synthesized_int_9 should be 5/12, but it is {}.".format(synthesized_int_9)
    assert synthesized_int_9.synthesized is True, "synthesized_int_9 should be synthesized."
    assert type(synthesized_int_9) == UntrustedFloat, "synthesized_int_9 type is not UntrustedFloat"


def untrusted_float_test():
    base_int = int("A", base=16)
    untrusted_int_1 = UntrustedInt(15)
    base_float = float(1.5)
    float_literal = 5.5
    untrusted_float_1 = UntrustedFloat(10.5)
    synthesized_float_1 = UntrustedFloat(12.5, synthesized=True)

    untrusted_float_2 = untrusted_float_1 + base_float
    assert untrusted_float_2 == 12, "untrusted_float_2 should be 12, but it is {}.".format(untrusted_float_2)
    assert untrusted_float_2.synthesized is False, "untrusted_float_2 should not be synthesized."
    assert type(untrusted_float_2) == type(untrusted_float_1), "untrusted_float_2 type is not UntrustedFloat"

    untrusted_float_3 = base_float + untrusted_float_1
    assert untrusted_float_3 == 12, "untrusted_float_3 should be 12, but it is {}.".format(untrusted_float_3)
    assert untrusted_float_3.synthesized is False, "untrusted_float_3 should not be synthesized."
    assert type(untrusted_float_3) == type(untrusted_float_1), "untrusted_float_3 type is not UntrustedFloat"

    untrusted_float_4 = base_int + untrusted_float_1
    assert untrusted_float_4 == 20.5, "untrusted_float_4 should be 20.5, but it is {}.".format(untrusted_float_4)
    assert untrusted_float_4.synthesized is False, "untrusted_float_4 should not be synthesized."
    assert type(untrusted_float_4) == type(untrusted_float_1), "untrusted_float_4 type is not UntrustedFloat"

    untrusted_float_5 = base_float - untrusted_float_1
    assert untrusted_float_5 == -9, "untrusted_float_5 should be -9, but it is {}.".format(untrusted_float_5)
    assert untrusted_float_5.synthesized is False, "untrusted_float_5 should not be synthesized."
    assert type(untrusted_float_5) == type(untrusted_float_1), "untrusted_float_5 type is not UntrustedFloat"

    untrusted_float_6 = base_int - untrusted_float_1
    assert untrusted_float_6 == -0.5, "untrusted_float_6 should be -0.5, but it is {}.".format(untrusted_float_6)
    assert untrusted_float_6.synthesized is False, "untrusted_float_6 should not be synthesized."
    assert type(untrusted_float_6) == type(untrusted_float_1), "untrusted_float_6 type is not UntrustedFloat"

    untrusted_float_7 = untrusted_int_1 - untrusted_float_1
    assert untrusted_float_7 == 4.5, "untrusted_float_7 should be 4.5, but it is {}.".format(untrusted_float_7)
    assert untrusted_float_7.synthesized is False, "untrusted_float_7 should not be synthesized."
    assert type(untrusted_float_7) == type(untrusted_float_1), "untrusted_float_7 type is not UntrustedFloat"

    untrusted_float_8 = untrusted_int_1 + untrusted_float_1 + base_float
    assert untrusted_float_8 == 27, "untrusted_float_8 should be 27, but it is {}.".format(untrusted_float_8)
    assert untrusted_float_8.synthesized is False, "untrusted_float_8 should not be synthesized."
    assert type(untrusted_float_8) == type(untrusted_float_1), "untrusted_float_8 type is not UntrustedFloat"

    synthesized_float_2 = float_literal * synthesized_float_1
    assert synthesized_float_2 == 68.75, "synthesized_float_2 should be 68.75, " \
                                         "but it is {}.".format(synthesized_float_2)
    assert synthesized_float_2.synthesized is True, "synthesized_float_2 should be synthesized."
    assert type(synthesized_float_2) == type(untrusted_float_1), "synthesized_float_2 type is not UntrustedFloat"


def untrusted_str_test():
    base_str = str("Hello ")
    str_literal = "World!"
    untrusted_str = UntrustedStr("Untrusted World!")
    synthesized_str = UntrustedStr("Fake World!", synthesized=True)
    # Some expected test cases
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


if __name__ == "__main__":
    untrusted_int_test()
    untrusted_float_test()
    untrusted_str_test()
