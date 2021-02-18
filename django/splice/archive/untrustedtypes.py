"""Untrusted classes."""

from decimal import Decimal
from datetime import datetime

from django.splice.archive.utils import UntrustedMixin


class UntrustedInt(UntrustedMixin, int):
    """
    Subclass Python trusted int class and UntrustedMixin.
    Note that synthesized is a *keyed* parameter.
    """

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @staticmethod
    def default_hash(input_integer):
        """
        Default hash function if no hash
        function is provided by the user.
        """
        return input_integer % (2 ** 63 - 1)

    custom_hash = default_hash

    @classmethod
    def set_hash(cls, new_hash_func):
        """
        Allows a developer to provide a custom hash
        function. The hash function must take an integer
        and returns an integer. Hash function must be
        Z3 friendly.
        """
        cls.custom_hash = new_hash_func

    def __hash__(self):
        """
        Override hash function to use either our default
        hash or the user-provided hash function. This function
        calls the helper function _untrusted_hash_() so that
        __hash__() output can be decorated.
        """
        return self._untrusted_hash_()

    def _untrusted_hash_(self):
        """Called by __hash__() but return a decorated value."""
        return type(self).custom_hash(self)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedInt(value, synthesized=flag)


class UntrustedFloat(UntrustedMixin, float):
    """Subclass Python trusted float class and UntrustedMixin."""

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedFloat(value, synthesized=flag)


class UntrustedStr(UntrustedMixin, str):
    """Subclass Python trusted str class and UntrustedMixin."""

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    # NOTE: Old implementation of subclassing UserString instead of str
    # def __init__(self, seq, *, synthesized=False):
    #     super().__init__(synthesized, seq)

    @staticmethod
    def default_hash(input_bytes):
        """
        Default hash function if no hash
        function is provided by the user.
        """
        h = 0
        for byte in input_bytes:
            h = h * 31 + byte
        return h

    custom_hash = default_hash

    @classmethod
    def set_hash(cls, new_hash_func):
        """
        Allows a developer to provide a custom hash
        function. The hash function must take a list of
        bytes and returns an integer; each byte should
        represent one character in string (in ASCII).
        Hash function must be Z3 friendly.
        """
        cls.custom_hash = new_hash_func

    def __hash__(self):
        """
        Override str hash function to use either
        the default or the user-provided hash function.
        This function calls the helper function
        _untrusted_hash_() so that __hash__() output
        can be decorated.
        """
        return self._untrusted_hash_()

    def _untrusted_hash_(self):
        """Called by __hash__() but return a decorated value."""
        chars = bytes(self, 'ascii')
        return type(self).custom_hash(chars)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedStr(value, synthesized=flag)

    def __radd__(self, other):
        """Define __radd__ so a str literal + an untrusted str returns an untrusted str."""
        synthesized = self.synthesized
        if isinstance(other, UntrustedMixin):
            synthesized |= other.synthesized
        return UntrustedStr(other.__add__(self), synthesized=synthesized)


class UntrustedBytes(UntrustedMixin, bytes):
    """
    Subclass Python builtin bytes class and UntrustedMixin.
    """

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedBytes(value, synthesized=flag)


class UntrustedBytearray(UntrustedMixin, bytearray):
    """
    Subclass Python builtin bytearray class and UntrustedMixin.
    bytearray is mutable so we need not define __new__ ourselves.
    """

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized, *args, **kwargs)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedBytearray(value, synthesized=flag)


class UntrustedDecimal(UntrustedMixin, Decimal):
    """
    Subclass Python decimal module's Decimal class and Untrusted Mixin.
    Decimal is immutable, so we should override __new__ and not just __init__.
    """

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @classmethod
    def untrustify(cls, value, flag):
        return UntrustedDecimal(value, synthesized=flag)


class UntrustedDatetime(UntrustedMixin, datetime):
    """
    Subclass Python datetime module's datetime class and Untrusted Mixin.
    datetime is immutable, so we should __new__ and not just __init__.
    This is also an example to showcase that it is easy to create a new
    untrusted type (class) from an existing Python class.
    """

    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    @classmethod
    def untrustify(cls, value, flag):
        year = value.year
        month = value.month
        day = value.day
        hour = value.hour
        minute = value.minute
        second = value.second
        microsecond = value.microsecond
        return UntrustedDatetime(year=year,
                                 month=month,
                                 day=day,
                                 hour=hour,
                                 minute=minute,
                                 second=second,
                                 microsecond=microsecond,
                                 synthesized=flag)


def int_test():
    base_int = int("A", base=16)
    int_literal = 5
    untrusted_int_1 = UntrustedInt(15)
    untrusted_int_2 = UntrustedInt("B", base=16)
    synthesized_int_1 = UntrustedInt(12, synthesized=True)

    # as_integer_ratio()
    r_x, r_y = untrusted_int_1.as_integer_ratio()
    assert r_x == 15
    assert r_y == 1
    assert r_x.synthesized is False
    assert r_y.synthesized is False
    assert type(r_x) == UntrustedInt
    assert type(r_y) == UntrustedInt

    r_x, r_y = synthesized_int_1.as_integer_ratio()
    assert r_x == 12
    assert r_y == 1
    assert r_x.synthesized is True
    assert r_y.synthesized is True
    assert type(r_x) == UntrustedInt
    assert type(r_y) == UntrustedInt

    r_x, r_y = base_int.as_integer_ratio()
    assert r_x == 10
    assert r_y == 1
    assert type(r_x) == int
    assert type(r_y) == int

    # FIXME: int_literal returns builtins int
    r_x, r_y = int_literal.as_integer_ratio()
    assert r_x == 5
    assert r_y == 1
    assert type(r_x) == builtins.int
    assert type(r_y) == builtins.int

    # bit_length()
    bl = untrusted_int_1.bit_length()
    assert bl == 4
    assert bl.synthesized is False
    assert type(bl) == UntrustedInt

    bl = synthesized_int_1.bit_length()
    assert bl == 4
    assert bl.synthesized is True
    assert type(bl) == UntrustedInt

    bl = base_int.bit_length()
    assert bl == 4
    assert type(bl) == int

    # FIXME: int_literal returns builtins int
    bl = int_literal.bit_length()
    assert bl == 3
    assert type(bl) == builtins.int

    # conjugate()
    c = untrusted_int_1.conjugate()
    assert c == untrusted_int_1
    assert c.synthesized is False
    assert type(c) == UntrustedInt

    c = synthesized_int_1.conjugate()
    assert c == synthesized_int_1
    assert c.synthesized is True
    assert type(c) == UntrustedInt

    c = base_int.conjugate()
    assert c == base_int
    assert type(c) == int

    # FIXME: int_literal returns builtins int
    bl = int_literal.conjugate()
    assert bl == 5
    assert type(bl) == builtins.int

    # from_bytes()
    i = UntrustedInt.from_bytes([1, 3, 4], byteorder='big')
    assert i == 66308
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = UntrustedInt.from_bytes([1, UntrustedInt(3, synthesized=True), 4], byteorder='big')
    assert i == 66308
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = int.from_bytes([UntrustedInt(1, synthesized=True), 3, 4], byteorder='big')
    assert i == 66308
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = int.from_bytes([1, 3, 4], byteorder='big')
    assert i == 66308
    assert type(i) == int

    # to_bytes()
    b = untrusted_int_1.to_bytes(10, 'big')
    assert type(b) == UntrustedBytes
    assert b.synthesized is False

    b = synthesized_int_1.to_bytes(10, 'big')
    assert type(b) == UntrustedBytes
    assert b.synthesized is True

    b = base_int.to_bytes(10, 'big')
    assert type(b) == bytes

    # FIXME: int_literal returns builtins int
    b = int_literal.to_bytes(10, 'big')
    assert type(b) == builtins.bytes

    # abs() (__abs__)
    i = abs(-untrusted_int_1)
    assert i == untrusted_int_1
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = (-untrusted_int_1).__abs__()
    assert i == untrusted_int_1
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = abs(-synthesized_int_1)
    assert i == synthesized_int_1
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = (-synthesized_int_1).__abs__()
    assert i == synthesized_int_1
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = abs(-base_int)
    assert i == base_int
    assert type(i) == int

    i = (-base_int).__abs__()
    assert i == base_int
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = abs(-int_literal)
    assert i == int_literal
    assert type(i) == builtins.int

    i = (-int_literal).__abs__()
    assert i == int_literal
    assert type(i) == builtins.int

    # + (__add__)
    i = untrusted_int_1 + untrusted_int_2
    assert i == 26
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1.__add__(untrusted_int_2)
    assert i == 26
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1 + base_int
    assert i == 25
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1.__add__(base_int)
    assert i == 25
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1 + int_literal
    assert i == 20
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1.__add__(int_literal)
    assert i == 20
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1 + untrusted_int_1
    assert i == 27
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__add__(untrusted_int_1)
    assert i == 27
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1 + int_literal
    assert i == 17
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__add__(int_literal)
    assert i == 17
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1 + base_int
    assert i == 22
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__add__(base_int)
    assert i == 22
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int + untrusted_int_1
    assert i == 25
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = base_int.__add__(untrusted_int_1)
    assert i == 25
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = int_literal + untrusted_int_1
    assert i == 20
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    # FIXME: int_literal works only with reflected methods (above), not with directly calling special method (below)
    i = int_literal.__add__(untrusted_int_1)
    assert i == 20
    assert type(i) == builtins.int

    i = int_literal + synthesized_int_1
    assert i == 17
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = int_literal.__add__(synthesized_int_1)
    assert i == 17
    assert type(i) == builtins.int

    i = int_literal + base_int
    assert i == 15
    assert type(i) == int

    i = int_literal.__add__(base_int)
    assert i == 15
    assert type(i) == builtins.int

    i = base_int + int_literal
    assert i == 15
    assert type(i) == int

    i = base_int.__add__(int_literal)
    assert i == 15
    assert type(i) == int

    # & (__and__) Similar behavior as + (__add__). Skip __or__.
    i = synthesized_int_1 & base_int
    assert i == 8
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int & untrusted_int_1
    assert i == 10
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = base_int & int_literal
    assert i == 0
    assert type(i) == int

    i = int_literal & base_int
    assert i == 0
    assert type(i) == int

    # TODO: __bool__ always returns bool

    # ceil() (__ceil__)
    i = math.ceil(untrusted_int_1)
    assert i == 15
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = math.ceil(synthesized_int_1)
    assert i == 12
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = math.ceil(base_int)
    assert i == 10
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = math.ceil(int_literal)
    assert i == 5
    assert type(i) == builtins.int

    # divmod() (__divmod__)
    d_x, d_y = divmod(untrusted_int_1, 4)
    assert d_x == 3
    assert d_y == 3
    assert d_x.synthesized is False
    assert d_y.synthesized is False
    assert type(d_x) == UntrustedInt
    assert type(d_y) == UntrustedInt

    d_x, d_y = divmod(15, UntrustedInt(4))
    assert d_x == 3
    assert d_y == 3
    assert d_x.synthesized is False
    assert d_y.synthesized is False
    assert type(d_x) == UntrustedInt
    assert type(d_y) == UntrustedInt

    d_x, d_y = divmod(synthesized_int_1, 4)
    assert d_x == 3
    assert d_y == 0
    assert d_x.synthesized is True
    assert d_y.synthesized is True
    assert type(d_x) == UntrustedInt
    assert type(d_y) == UntrustedInt

    d_x, d_y = divmod(base_int, 4)
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int

    d_x, d_y = divmod(10, int(4))
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int

    # FIXME: int_literal works only with reflected methods (above), not with directly calling special method (below)
    d_x, d_y = int_literal.__divmod__(int(4))
    assert d_x == 1
    assert d_y == 1
    assert type(d_x) == builtins.int
    assert type(d_y) == builtins.int

    # FIXME: int_literal returns builtins int
    d_x, d_y = divmod(int_literal, 4)
    assert d_x == 1
    assert d_y == 1
    assert type(d_x) == builtins.int
    assert type(d_y) == builtins.int

    # == (__eq__)
    assert untrusted_int_1 == 15
    assert untrusted_int_1 == int(15)
    assert synthesized_int_1 == UntrustedInt(12)
    assert 15 == untrusted_int_1
    assert int_literal == int(5)
    assert 12 == synthesized_int_1

    # float() (__float__)
    try:
        float(synthesized_int_1)
    except TypeError as e:
        print("12 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert synthesized_int_1.to_trusted(forced=True) == 12
    assert type(float(synthesized_int_1.to_trusted(forced=True))) == float

    try:
        synthesized_int_1.__float__()
    except TypeError as e:
        print("12 is synthesized, converting it to float using __float__ results in "
              "TypeError: {error}".format(error=e))
    assert synthesized_int_1.to_trusted(forced=True) == 12
    assert type(synthesized_int_1.to_trusted(forced=True).__float__()) == float

    try:
        float(untrusted_int_1)
    except TypeError as e:
        print("15 is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_int_1.to_trusted() == 15
    assert type(float(untrusted_int_1.to_trusted())) == float

    try:
        untrusted_int_1.__float__()
    except TypeError as e:
        print("15 is untrusted, converting it to float using __float__ results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_int_1.to_trusted() == 15
    assert type(untrusted_int_1.to_trusted().__float__()) == float

    assert float(base_int) == 10
    assert type(float(base_int)) == float

    assert base_int.__float__() == 10
    assert type(base_int.__float__()) == float

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast float() to type float. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in float is shadowed by our own float, Python
    #  ensures return value to be our float. However, the same enforcement
    #  does not apply when __float__ is called directly from an int literal
    assert float(int_literal) == 5
    assert type(float(int_literal)) == float

    assert int_literal.__float__() == 5
    assert type(int_literal.__float__()) == builtins.float

    # // (__floordiv__)
    i = untrusted_int_1 // 4
    assert i == 3
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = 15 // UntrustedInt(4)
    assert i == 3
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1 // 4
    assert i == 3
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int // 4
    assert i == 2
    assert type(i) == int

    i = base_int.__floordiv__(4)
    assert i == 2
    assert type(i) == int

    i = 10 // int(4)
    assert i == 2
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal.__floordiv__(int(4))
    assert i == 1
    assert type(i) == builtins.int

    i = 10 // 4
    assert i == 2
    assert type(i) == builtins.int

    # floor() (__floor__)
    i = math.floor(untrusted_int_1)
    assert i == untrusted_int_1
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = math.floor(synthesized_int_1)
    assert i == synthesized_int_1
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = math.floor(base_int)
    assert i == base_int
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = math.floor(int_literal)
    assert i == int_literal
    assert type(i) == builtins.int

    # format() (__format__)
    try:
        "{}".format(untrusted_int_1)
    except TypeError as e:
        print("15 is untrusted, converting it to str using format() results in "
              "TypeError: {error}".format(error=e))
    s = untrusted_int_1.to_trusted()
    assert type(format(s)) == str

    try:
        "{}".format(synthesized_int_1)
    except TypeError as e:
        print("12 is untrusted, converting it to str using format() results in "
              "TypeError: {error}".format(error=e))
    s = synthesized_int_1.to_trusted(forced=True)
    assert type(format(s)) == str

    s = format(base_int)
    assert type(s) == str

    # FIXME: int_literal format() returns builtins str
    s = format(int_literal)
    assert type(s) == builtins.str

    # >= (__ge__) # Skip similar methods: __gt__, __le__, __Lt__, __ne__
    assert untrusted_int_1 >= 15
    assert untrusted_int_1 >= int(15)
    assert synthesized_int_1 >= UntrustedInt(12)
    assert 15 >= untrusted_int_1
    assert int_literal >= int(5)
    assert 12 >= synthesized_int_1

    # hash() (__hash__)
    h = hash(untrusted_int_1)
    assert h.synthesized is False
    assert type(h) == UntrustedInt

    h = untrusted_int_1.__hash__()
    assert h.synthesized is False
    assert type(h) == UntrustedInt

    h = hash(synthesized_int_1)
    assert h.synthesized is True
    assert type(h) == UntrustedInt

    h = synthesized_int_1.__hash__()
    assert h.synthesized is True
    assert type(h) == UntrustedInt

    h = hash(base_int)
    assert type(h) == int

    h = base_int.__hash__()
    assert type(h) == int

    # FIXME: int_literal returns builtins int
    h = hash(int_literal)
    assert type(h) == builtins.int

    h = int_literal.__hash__()
    assert type(h) == builtins.int

    # __index__
    i = untrusted_int_1.__index__()
    assert i == 15
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__index__()
    assert i == 12
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int.__index__()
    assert i == 10
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal.__index__()
    assert i == 5
    assert type(i) == builtins.int

    # int() (__int__)
    try:
        int(synthesized_int_1)
    except TypeError as e:
        print("12 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    try:
        synthesized_int_1.__int__()
    except TypeError as e:
        print("12 is synthesized, converting it to int using __int__ results in "
              "TypeError: {error}".format(error=e))
    try:
        synthesized_int_1.to_trusted()
    except RuntimeError as e:
        print("12 is synthesized, converting it to int using to_trusted() without force results in "
              "RuntimeError: {error}".format(error=e))
    assert type(synthesized_int_1.to_trusted(forced=True)) == int

    try:
        int(untrusted_int_1)
    except TypeError as e:
        print("15 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    try:
        untrusted_int_1.__int__()
    except TypeError as e:
        print("15 is untrusted, converting it to int using __int__ results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_int_1.to_trusted() == untrusted_int_1
    assert type(untrusted_int_1.to_trusted()) == int

    assert int(base_int) == base_int
    assert type(int(base_int)) == int

    assert base_int.__int__() == base_int
    assert type(base_int.__int__()) == int

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast int() to type int. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in int is shadowed by our own float, Python
    #  ensures return value to be our int. However, the same enforcement
    #  does not apply when __int__ is called directly from an int literal
    assert int(int_literal) == int_literal
    assert type(int(int_literal)) == int

    assert int_literal.__int__() == int_literal
    assert type(int_literal.__int__()) == builtins.int

    # ~ (__invert__)
    i = ~untrusted_int_1
    assert i == -16
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1.__invert__()
    assert i == -16
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = ~synthesized_int_1
    assert i == -13
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__invert__()
    assert i == -13
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = ~base_int
    assert i == -11
    assert type(i) == int

    i = base_int.__invert__()
    assert i == -11
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = ~int_literal
    assert i == -6
    assert type(i) == builtins.int

    i = int_literal.__invert__()
    assert i == -6
    assert type(i) == builtins.int

    # << (__lshift__)
    i = untrusted_int_1 << 3
    assert i == 120
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = 15 << UntrustedInt(3)
    assert i == 120
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1 << 3
    assert i == 96
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = 12 << UntrustedInt(3, synthesized=True)
    assert i == 96
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int << 3
    assert i == 80
    assert type(i) == int

    i = 10 << int(3)
    assert i == 80
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal << 3
    assert i == 40
    assert type(i) == builtins.int

    # % (__mod__)
    i = untrusted_int_1 % 4
    assert i == 3
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = 15 % UntrustedInt(4)
    assert i == 3
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1 % 4
    assert i == 0
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int % 4
    assert i == 2
    assert type(i) == int

    i = int_literal % int(4)
    assert i == 1
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal % 4
    assert i == 1
    assert type(i) == builtins.int

    # * (__mul__)
    i = int_literal * synthesized_int_1
    assert i == 60
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = int_literal * untrusted_int_1
    assert i == 75
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = int_literal * base_int
    assert i == 50
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal * int_literal
    assert i == 25
    assert type(i) == builtins.int

    i = int_literal.__mul__(base_int)
    assert i == 50
    assert type(i) == builtins.int

    # - (__neg__)
    i = -untrusted_int_1
    assert i == -15
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = -synthesized_int_1
    assert i == -12
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = -base_int
    assert i == -10
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = -int_literal
    assert i == -5
    assert type(i) == builtins.int

    # | (__or__): similar to __and__.

    # Skip + (__pos__). Similar to __neg__.

    # ** (__pow__)
    i = untrusted_int_1 ** 2
    assert i == 225
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = 15 ** UntrustedInt(2)
    assert i == 225
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1 ** 2
    assert i == 144
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int ** 2
    assert i == 100
    assert type(i) == int

    i = base_int.__pow__(2)
    assert i == 100
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal.__pow__(int(2))
    assert i == 25
    assert type(i) == builtins.int

    i = int_literal ** 2
    assert i == 25
    assert type(i) == builtins.int

    # All reflected (swapped) methods are skipped -- should work as expected.
    # __radd__, __rand__, __rdivmod__, __rfloordiv__, __rlshift__, __rmod__, __rmul__,
    # __ror__, __rpow__, __rrshift__, __rsub__, __rtruediv__, __rxor__

    # repr() (__repr__)
    try:
        repr(untrusted_int_1)
    except TypeError as e:
        print("15 is untrusted, converting it to str using repr() results in "
              "TypeError: {error}".format(error=e))
    try:
        untrusted_int_1.__repr__()
    except TypeError as e:
        print("15 is untrusted, converting it to str using __repr__ results in "
              "TypeError: {error}".format(error=e))
    s = untrusted_int_1.to_trusted()
    assert type(repr(s)) == str

    try:
        repr(synthesized_int_1)
    except TypeError as e:
        print("12 is untrusted, converting it to str using repr() results in "
              "TypeError: {error}".format(error=e))
    try:
        synthesized_int_1.__repr__()
    except TypeError as e:
        print("12 is untrusted, converting it to str using __repr__ results in "
              "TypeError: {error}".format(error=e))
    s = synthesized_int_1.to_trusted(forced=True)
    assert type(repr(s)) == str

    s = repr(base_int)
    assert type(s) == str

    s = base_int.__repr__()
    assert type(s) == str

    # FIXME: int_literal repr() and __repr__ return builtins str
    s = repr(int_literal)
    assert type(s) == builtins.str

    s = int_literal.__repr__()
    assert type(s) == builtins.str

    # round() (__round__)
    i = round(untrusted_int_1)
    assert i == 15
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = untrusted_int_1.__round__()
    assert i == 15
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = round(synthesized_int_1)
    assert i == 12
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__round__()
    assert i == 12
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = round(base_int)
    assert i == 10
    assert type(i) == int

    i = base_int.__round__()
    assert i == 10
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = round(int_literal)
    assert i == 5
    assert type(i) == builtins.int

    i = int_literal.__round__()
    assert i == 5
    assert type(i) == builtins.int

    # Skip >> (__rshift__), same as << (__lshift__).

    # __sizeof__
    i = untrusted_int_1.__sizeof__()
    assert i == 28
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = synthesized_int_1.__sizeof__()
    assert i == 28
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = base_int.__sizeof__()
    assert i == 28
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = int_literal.__sizeof__()
    assert i == 28
    assert type(i) == builtins.int

    # Skip - (__sub__), same as + (__add__)

    # / (__truediv__)
    i = synthesized_int_1 / int_literal
    assert i == 2.4
    assert i.synthesized is True
    assert type(i) == UntrustedFloat

    i = synthesized_int_1.__truediv__(int_literal)
    assert i == 2.4
    assert i.synthesized is True
    assert type(i) == UntrustedFloat

    i = int_literal / synthesized_int_1
    assert i == 5 / 12
    assert i.synthesized is True
    assert type(i) == UntrustedFloat

    i = base_int / 12
    assert i == 10 / 12
    assert type(i) == float

    i = 12 / base_int
    assert i == 12 / 10
    assert type(i) == float

    # FIXME: int_literal returns builtins float
    i = int_literal.__truediv__(base_int)
    assert i == 0.5
    assert type(i) == builtins.float

    i = int_literal / 12
    assert i == 5 / 12
    assert type(i) == builtins.float

    # trunc() (__trunc__)
    i = math.trunc(untrusted_int_1)
    assert i == untrusted_int_1
    assert i.synthesized is False
    assert type(i) == UntrustedInt

    i = math.trunc(synthesized_int_1)
    assert i == synthesized_int_1
    assert i.synthesized is True
    assert type(i) == UntrustedInt

    i = math.trunc(base_int)
    assert i == base_int
    assert type(i) == int

    # FIXME: int_literal returns builtins int
    i = math.trunc(int_literal)
    assert i == int_literal
    assert type(i) == builtins.int

    # Skip ^ (__xor__), same as | (__or__)

    # str() (__str__)
    try:
        str(synthesized_int_1)
    except TypeError as e:
        print("12 is synthesized, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    try:
        str(untrusted_int_1)
    except TypeError as e:
        print("15 is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    assert str(untrusted_int_1.to_trusted()) == "15"
    assert type(str(untrusted_int_1.to_trusted())) == str

    assert str(base_int) == "10"
    assert type(str(base_int)) == str

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast str() to type str. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in str is shadowed by our own str, Python
    #  ensures return value to be our str. However, the same enforcement
    #  does not apply when __str__ is called directly from an int literal
    assert str(int_literal) == "5"
    assert type(str(int_literal)) == str

    assert int_literal.__str__() == "5"
    assert type(int_literal.__str__()) == builtins.str


def float_test():
    base_int = int("A", base=16)
    untrusted_int_1 = UntrustedInt(15)
    base_float = float(10.5)
    float_literal = 10.5
    untrusted_float_1 = UntrustedFloat(10.5)
    synthesized_float_1 = UntrustedFloat(10.5, synthesized=True)

    # as_integer_ratio()
    r_x, r_y = untrusted_float_1.as_integer_ratio()
    assert r_x == 21
    assert r_y == 2
    assert r_x.synthesized is False
    assert r_y.synthesized is False
    assert type(r_x) == UntrustedInt
    assert type(r_y) == UntrustedInt

    r_x, r_y = synthesized_float_1.as_integer_ratio()
    assert r_x == 21
    assert r_y == 2
    assert r_x.synthesized is True
    assert r_y.synthesized is True
    assert type(r_x) == UntrustedInt
    assert type(r_y) == UntrustedInt

    r_x, r_y = base_float.as_integer_ratio()
    assert r_x == 21
    assert r_y == 2
    assert type(r_x) == int
    assert type(r_y) == int

    # FIXME: float_literal returns builtins int
    r_x, r_y = float_literal.as_integer_ratio()
    assert r_x == 21
    assert r_y == 2
    assert type(r_x) == builtins.int
    assert type(r_y) == builtins.int

    # conjugate()
    c = untrusted_float_1.conjugate()
    assert c == untrusted_float_1
    assert c.synthesized is False
    assert type(c) == UntrustedFloat

    c = synthesized_float_1.conjugate()
    assert c == synthesized_float_1
    assert c.synthesized is True
    assert type(c) == UntrustedFloat

    c = base_float.conjugate()
    assert c == base_float
    assert type(c) == float

    # FIXME: float_literal returns builtins float
    c = float_literal.conjugate()
    assert c == float_literal
    assert type(c) == builtins.float

    # fromhex()
    f = float.fromhex('0x1.ffffp10')
    assert f == 2047.984375
    assert type(f) == float

    f = float.fromhex(str('0x1.ffffp10'))
    assert f == 2047.984375
    assert type(f) == float

    f = float.fromhex(UntrustedStr('0x1.ffffp10'))
    assert f == 2047.984375
    assert f.synthesized is False
    assert type(f) == UntrustedFloat

    f = float.fromhex(UntrustedStr('0x1.ffffp10', synthesized=True))
    assert f == 2047.984375
    assert f.synthesized is True
    assert type(f) == UntrustedFloat

    # hex()
    s = untrusted_float_1.hex()
    assert s == '0x1.5000000000000p+3'
    assert s.synthesized is False
    assert type(s) == UntrustedStr

    s = synthesized_float_1.hex()
    assert s == '0x1.5000000000000p+3'
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    s = base_float.hex()
    assert s == '0x1.5000000000000p+3'
    assert type(s) == str

    # FIXME: float_literal returns builtins str
    s = float_literal.hex()
    assert s == '0x1.5000000000000p+3'
    assert type(s) == builtins.str

    # is_integer()
    assert untrusted_float_1.is_integer() is False
    assert synthesized_float_1.is_integer() is False
    assert float_literal.is_integer() is False
    assert base_float.is_integer() is False

    # __abs__, __add__, __divmod__, __hash__, __mod__, __mul__, __neg__, __pos__, __pow__,
    # __sub__, __truediv__, __trunc__  and their corresponding reflected (swapped) methods
    # should behave similarly as int. We just test + (__add__) for simplicity.
    i = untrusted_float_1 + base_float
    assert i == 21
    assert i.synthesized is False
    assert type(i) == UntrustedFloat

    i = base_float + untrusted_float_1
    assert i == 21
    assert i.synthesized is False
    assert type(i) == UntrustedFloat

    i = base_int + untrusted_float_1
    assert i == 20.5
    assert i.synthesized is False
    assert type(i) == UntrustedFloat

    i = base_float + float_literal
    assert i == 21
    assert type(i) == float

    i = float_literal + base_float
    assert i == 21
    assert type(i) == float

    i = float_literal + synthesized_float_1
    assert i == 21
    assert i.synthesized is True
    assert type(i) == UntrustedFloat

    # FIXME: int_literal works only with reflected methods (above), not with directly calling special method (below)
    i = float_literal.__add__(synthesized_float_1)
    assert i == 21
    assert type(i) == builtins.float

    # TODO: __bool__ always returns bool

    # __eq__, __ge__, __gt__, etc. should behave similarly as int.

    # float() (__float__)
    try:
        float(synthesized_float_1)
    except TypeError as e:
        print("10.5 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert synthesized_float_1.to_trusted(forced=True) == 10.5
    assert type(float(synthesized_float_1.to_trusted(forced=True))) == float

    try:
        synthesized_float_1.__float__()
    except TypeError as e:
        print("10.5 is synthesized, converting it to float using __float__ results in "
              "TypeError: {error}".format(error=e))
    assert synthesized_float_1.to_trusted(forced=True) == 10.5
    assert type(synthesized_float_1.to_trusted(forced=True).__float__()) == float

    assert float(base_float) == 10.5
    assert type(float(base_float)) == float

    assert base_float.__float__() == 10.5
    assert type(base_float.__float__()) == float

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast float() to type float. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in float is shadowed by our own float, Python
    #  ensures return value to be our float. However, the same enforcement
    #  does not apply when __float__ is called directly from an int literal
    assert float(float_literal) == 10.5
    assert type(float(float_literal)) == float

    assert float_literal.__float__() == 10.5
    assert type(float_literal.__float__()) == builtins.float

    # format() (__format__), str() (__str__), repr(__repr__) behave similarly
    try:
        "{}".format(untrusted_float_1)
    except TypeError as e:
        print("10.5 is untrusted, converting it to str using format() results in "
              "TypeError: {error}".format(error=e))
    s = untrusted_float_1.to_trusted()
    assert type(format(s)) == str

    try:
        "{}".format(synthesized_float_1)
    except TypeError as e:
        print("10.5 is untrusted, converting it to str using format() results in "
              "TypeError: {error}".format(error=e))
    s = synthesized_float_1.to_trusted(forced=True)
    assert type(format(s)) == str

    s = format(base_float)
    assert type(s) == str

    # FIXME: float_literal format() returns builtins str
    s = format(float_literal)
    assert type(s) == builtins.str

    # int() __int__
    try:
        int(untrusted_float_1)
    except TypeError as e:
        print("10.0 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(untrusted_float_1.to_trusted()) == 10
    assert type(int(untrusted_float_1.to_trusted())) == int

    try:
        int(synthesized_float_1)
    except TypeError as e:
        print("10.0 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(synthesized_float_1.to_trusted(forced=True)) == 10
    assert type(int(synthesized_float_1.to_trusted(forced=True))) == int

    assert int(base_float) == 10
    assert type(int(base_float)) == int

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast int() to type int. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in int is shadowed by our own int, Python
    #  ensures return value to be our int. However, the same enforcement
    #  does not apply when __int__ is called directly from an int literal
    assert int(float_literal) == 10
    assert type(int(float_literal)) == int

    assert float_literal.__int__() == 10
    assert type(float_literal.__int__()) == builtins.int


def str_test():
    base_str = str("Hello")
    str_literal = "World"
    untrusted_str = UntrustedStr("untrusted")
    synthesized_str = UntrustedStr("synthesized", synthesized=True)

    # capitalize()
    s = base_str.capitalize()
    assert s == "Hello"
    assert type(s) == str
    s = untrusted_str.capitalize()
    assert s == "Untrusted"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.capitalize()
    assert s == "Synthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.capitalize()
    assert s == "World"
    assert type(s) == builtins.str

    # casefold()
    s = base_str.casefold()
    assert s == "hello"
    assert type(s) == str
    s = untrusted_str.casefold()
    assert s == "untrusted"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.casefold()
    assert s == "synthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.casefold()
    assert s == "world"
    assert type(s) == builtins.str

    # center()
    s = base_str.center(10, "x")
    assert s == "xxHelloxxx"
    assert type(s) == str
    s = untrusted_str.center(11, "x")
    assert s == "xuntrustedx"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.center(13)
    assert s == " synthesized "
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.center(9)
    assert s == "  World  "
    assert type(s) == builtins.str

    # count()
    c = base_str.count("e")
    assert c == 1
    assert type(c) == int
    c = base_str.count("e", UntrustedInt(0))
    assert c == 1
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = base_str.count(UntrustedStr("e", synthesized=True))
    assert c == 1
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = untrusted_str.count("u")
    assert c == 2
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = untrusted_str.count("u", UntrustedInt(0, synthesized=True))
    assert c == 2
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = synthesized_str.count("s")
    assert c == 2
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    # FIXME: str_literal returns builtins int
    c = str_literal.count(UntrustedStr("d"))
    assert c == 1
    assert type(c) == builtins.int

    # encode()
    b = base_str.encode()
    assert type(b) == bytes

    b = untrusted_str.encode()
    assert type(b) == UntrustedBytes
    assert b.synthesized is False

    b = synthesized_str.encode()
    assert type(b) == UntrustedBytes
    assert b.synthesized is True

    # FIXME: str_literal returns builtins bytes
    b = str_literal.encode()
    assert type(b) == builtins.bytes

    # endswith()
    b = base_str.endswith("o")
    assert b is True
    b = base_str.endswith(UntrustedStr("o"))
    assert b is True
    # Note: bool values remain bool. Skip testing other methods that return bool
    # isalnum(), isalpha(), isascii(), isdecimal(), isdigit(), isidentifier(),
    # islower(), isnumeric(), isprintable(), isspace(), istitle(), isupper(), startswith(),
    # __eq__, __ge__, __gt__, __le__, __lt__, __ne__, __contains__

    # expandtabs()
    s = base_str.expandtabs()
    assert s == "Hello"
    assert type(s) == str
    s = untrusted_str.expandtabs()
    assert s == "untrusted"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.expandtabs()
    assert s == "synthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.expandtabs()
    assert s == "World"
    assert type(s) == builtins.str

    # find()
    c = base_str.find("e")
    assert c == 1
    assert type(c) == int
    c = base_str.find("e", UntrustedInt(0))
    assert c == 1
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = base_str.find(UntrustedStr("e", synthesized=True))
    assert c == 1
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = untrusted_str.find("u")
    assert c == 0
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = untrusted_str.find("u", UntrustedInt(0, synthesized=True))
    assert c == 0
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = synthesized_str.find("s")
    assert c == 0
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    # FIXME: str_literal returns builtins str
    c = str_literal.find(UntrustedStr("d"))
    assert c == 4
    assert type(s) == builtins.str

    # format()
    try:
        str("Hello {place}").format(place=UntrustedStr("world"))
    except TypeError as e:
        print("'Hello world' is untrusted, formatting it using format() results in "
              "TypeError: {error}".format(error=e))
    # FIXME: IMPORTANT NOTE ===============================================
    #  Although string literal is the calling object, when the string to be
    #  formatted is untrusted, Splice returns TypeError. This is because the
    #  untrusted string also calls __format__, at which point intercepted by
    #  Splice. However, if the string can be returned (e.g., because the
    #  formatted str is trust-aware), the return str will be of built-in type.
    #  This applies to format_map() as well.
    s_literal = "Hello {place}"
    s = s_literal.format(place=str("world"))
    assert s == "Hello world"
    assert type(s) == builtins.str
    try:
        s_literal.format(place=UntrustedStr("world", synthesized=True))
    except TypeError as e:
        print("'world' is synthesized, formatting it using format() results in "
              "TypeError: {error}".format(error=e))

    # format_map()
    m = {"place": "World", "place2": UntrustedStr("Untrusted World")}
    s_literal = "Hello {place}; Hi {place2}"
    try:
        s_literal.format(**m)
    except TypeError as e:
        print("'Untrusted World' is untrusted, formatting it using format() results in "
              "TypeError: {error}".format(error=e))
    m = {"place": "World", "place2": str("Untrusted World")}
    s = s_literal.format(**m)
    assert s == "Hello World; Hi Untrusted World"
    assert type(s) == builtins.str

    # index()
    c = base_str.index("e")
    assert c == 1
    assert type(c) == int
    c = base_str.index("e", UntrustedInt(0))
    assert c == 1
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = base_str.index(UntrustedStr("e", synthesized=True))
    assert c == 1
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = untrusted_str.index("u")
    assert c == 0
    assert c.synthesized is False
    assert type(c) == UntrustedInt
    c = untrusted_str.index("u", UntrustedInt(0, synthesized=True))
    assert c == 0
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    c = synthesized_str.index("s")
    assert c == 0
    assert c.synthesized is True
    assert type(c) == UntrustedInt
    # FIXME: str_literal returns builtins str
    c = str_literal.index(UntrustedStr("d"))
    assert c == 4
    assert type(s) == builtins.str

    # join()
    base_s = str(".")
    s = base_s.join(["Hello", "world"])
    assert s == "Hello.world"
    assert type(s) == str

    s = base_s.join(["Hello", UntrustedStr("world")])
    assert s.to_trusted() == "Hello.world"
    assert s.synthesized is False
    assert type(s) == UntrustedStr

    s = base_s.join(["Hello", UntrustedStr("world", synthesized=True)])
    assert s.to_trusted(forced=True) == "Hello.world"
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    untrusted_s = UntrustedStr(".")
    s = untrusted_s.join(["Hello", UntrustedStr("world", synthesized=True)])
    assert s.to_trusted(forced=True) == "Hello.world"
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    synthesized_s = UntrustedStr(".", synthesized=True)
    s = synthesized_s.join(["Hello", "world"])
    assert s.to_trusted(forced=True) == "Hello.world"
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    s_literal = "."
    s = s_literal.join([str("Hello"), "world"])
    assert s == "Hello.world"
    assert type(s) == builtins.str

    # FIXME: str_literal returns builtins str
    s_literal = "."
    s = s_literal.join([UntrustedStr("Hello"), "world"])
    assert s == "Hello.world"
    assert type(s) == builtins.str

    # ljust()
    s = base_str.ljust(10)
    assert type(s) == str
    s = base_str.ljust(UntrustedInt(10))
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = base_str.ljust(UntrustedInt(10, synthesized=True))
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    s = untrusted_str.ljust(UntrustedInt(10, synthesized=True))
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    s = synthesized_str.ljust(13)
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.ljust(UntrustedInt(9))
    assert type(s) == builtins.str

    # lower()
    s = base_str.lower()
    assert s == "hello"
    assert type(s) == str
    s = untrusted_str.lower()
    assert s == "untrusted"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.lower()
    assert s == "synthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.lower()
    assert s == "world"
    assert type(s) == builtins.str

    # lstrip() (skip strip() as they are similar)
    s = base_str.lstrip()
    assert s == "Hello"
    assert type(s) == str
    s = base_str.lstrip(UntrustedStr("H"))
    assert s == "ello"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = untrusted_str.lstrip()
    assert s == "untrusted"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = untrusted_str.lstrip(UntrustedStr("d", synthesized=True))
    assert s == "untrusted"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    s = synthesized_str.lstrip()
    assert s == "synthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.lstrip()
    assert s == "World"
    assert type(s) == builtins.str
    s = str_literal.lstrip(UntrustedStr("W", synthesized=True))
    assert s == "orld"
    assert type(s) == builtins.str

    # partition()
    s_front, s_sep, s_back = base_str.partition("e")
    assert type(s_front) == str
    assert type(s_sep) == str
    assert type(s_back) == str

    s_front, s_sep, s_back = base_str.partition(UntrustedStr("e"))
    assert type(s_front) == UntrustedStr
    assert s_front.synthesized is False
    assert type(s_sep) == UntrustedStr
    assert s_sep.synthesized is False
    assert type(s_back) == UntrustedStr
    assert s_back.synthesized is False

    s_front, s_sep, s_back = base_str.partition(UntrustedStr("e", synthesized=True))
    assert type(s_front) == UntrustedStr
    assert s_front.synthesized is True
    assert type(s_sep) == UntrustedStr
    assert s_sep.synthesized is True
    assert type(s_back) == UntrustedStr
    assert s_back.synthesized is True

    s_front, s_sep, s_back = untrusted_str.partition("u")
    assert type(s_front) == UntrustedStr
    assert s_front.synthesized is False
    assert type(s_sep) == UntrustedStr
    assert s_sep.synthesized is False
    assert type(s_back) == UntrustedStr
    assert s_back.synthesized is False

    # FIXME: str_literal returns builtins str
    s_front, s_sep, s_back = str_literal.partition(UntrustedStr("e", synthesized=True))
    assert type(s_front) == builtins.str
    assert type(s_sep) == builtins.str
    assert type(s_back) == builtins.str

    # replace()
    s = base_str.replace("e", "a")
    assert s == "Hallo"
    assert type(s) == str
    s = base_str.replace("e", UntrustedStr("a"))
    assert type(s) == UntrustedStr
    assert s.synthesized is False
    s = base_str.replace(UntrustedStr("e"), "a")
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = untrusted_str.replace("n", "-")
    assert type(s) == UntrustedStr
    assert s.synthesized is False
    s = untrusted_str.replace("n", UntrustedStr("-", synthesized=True))
    assert type(s) == UntrustedStr
    assert s.synthesized is True

    # FIXME: str_literal returns builtins str
    s = str_literal.replace("d", str("t"))
    assert s == "Worlt"
    assert type(s) == builtins.str
    s = str_literal.replace("d", UntrustedStr("t"))
    assert s == "Worlt"
    assert type(s) == builtins.str

    # Reversed methods are the same as the non-reversed one, skip testing:
    # rfind(), rindex(), rjust(), rpartition(), rsplit(), rstrip(),

    # split() (skip splitlines() as they are similar)
    l = base_str.split("e")
    for e in l:
        assert type(e) == str
    l = base_str.split(UntrustedStr("e"))
    for e in l:
        assert type(e) == UntrustedStr
        assert e.synthesized is False
    l = untrusted_str.split(UntrustedStr("s", synthesized=True))
    for e in l:
        assert type(e) == UntrustedStr
        assert e.synthesized is True
    # FIXME: str_literal returns builtins str
    l = str_literal.split(UntrustedStr("l", synthesized=True))
    for e in l:
        assert type(e) == builtins.str

    # swapcase() (skip title() and upper(), as they are similar)
    s = base_str.swapcase()
    assert s == "hELLO"
    assert type(s) == str
    s = untrusted_str.swapcase()
    assert s == "UNTRUSTED"
    assert s.synthesized is False
    assert type(s) == UntrustedStr
    s = synthesized_str.swapcase()
    assert s == "SYNTHESIZED"
    assert s.synthesized is True
    assert type(s) == UntrustedStr
    # FIXME: str_literal returns builtins str
    s = str_literal.swapcase()
    assert s == "wORLD"
    assert type(s) == builtins.str

    # TODO: test translate() and maketrans() together

    # zfill()
    s = str("123")
    s = s.zfill(5)
    assert s == "00123"
    assert type(s) == str

    s = str("123")
    s = s.zfill(UntrustedInt(5))
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = UntrustedStr("123")
    s = s.zfill(5)
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = UntrustedStr("123")
    s = s.zfill(UntrustedInt(5, synthesized=True))
    assert type(s) == UntrustedStr
    assert s.synthesized is True

    # FIXME: str_literal returns builtins str
    s = "123"
    s = s.zfill(UntrustedInt(5, synthesized=True))
    assert type(s) == builtins.str

    # __add__
    s = untrusted_str + base_str
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = base_str + untrusted_str
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = base_str + synthesized_str
    assert type(s) == UntrustedStr
    assert s.synthesized is True

    s = base_str + " world"
    assert s == "Hello world"
    assert type(s) == str

    s = untrusted_str + str_literal
    assert s.synthesized is False
    assert type(s) == UntrustedStr

    s = synthesized_str + base_str
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    s = synthesized_str + str_literal
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    # FIXME: IMPORTANT NOTE ======================================================
    #  We define __radd__ in the untrusted and trust-aware str classes, so that
    #  the reflected method would be called when a str literal is the left operand.
    #  However, this works only with reflected methods, not with directly calling
    #  special method.
    s = str_literal + base_str
    assert s == "WorldHello"
    assert type(s) == str

    s = str_literal.__add__(base_str)
    assert s == "WorldHello"
    assert type(s) == builtins.str

    s = str_literal + synthesized_str
    assert s.to_trusted(forced=True) == "Worldsynthesized"
    assert s.synthesized is True
    assert type(s) == UntrustedStr

    s = str_literal.__add__(synthesized_str)
    assert s == "Worldsynthesized"
    assert type(s) == builtins.str

    h = hash(base_str)
    assert type(h) == int
    h = hash(untrusted_str)
    assert type(h) == UntrustedInt
    assert h.synthesized is False
    h = hash(synthesized_str)
    assert type(h) == UntrustedInt
    assert h.synthesized is True
    # FIXME: str_literal returns builtins str
    h = hash(str_literal)
    assert type(h) == builtins.int

    # __iter__
    # IMPORTANT NOTE: We define __iter__ in the untrusted and trust-aware str classes
    for s in base_str:
        assert type(s) == str
    for s in untrusted_str:
        assert type(s) == UntrustedStr
        assert s.synthesized is False
    for s in synthesized_str:
        assert type(s) == UntrustedStr
        assert s.synthesized is True
    # FIXME: str_literal returns builtins str
    for s in str_literal:
        assert type(s) == builtins.str

    # __len__
    l = len(base_str)
    assert l == 5
    assert type(l) == int

    l = len(untrusted_str)
    assert l == 9
    assert type(l) == UntrustedInt
    assert l.synthesized is False

    l = len(synthesized_str)
    assert l == 11
    assert type(l) == UntrustedInt
    assert l.synthesized is True

    # FIXME: str_literal returns builtins str
    l = len(str_literal)
    assert l == 5
    assert type(l) == builtins.int

    # TODO: __mod__ is not tested

    # * (__mul__, __rmul__)
    s = base_str * 5
    assert type(s) == str

    s = base_str * UntrustedInt(5)
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = base_str * UntrustedInt(5, synthesized=True)
    assert type(s) == UntrustedStr
    assert s.synthesized is True

    s = untrusted_str * 5
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    s = synthesized_str * 5
    assert type(s) == UntrustedStr
    assert s.synthesized is True

    # FIXME: str_literal returns builtins str,
    #  even through __mul__ has a reflected method __rmul__,
    #  because __rmul__ is for a different use! For
    #  str multiplication, str must be either untrusted
    #  or trust-aware to propagate untrustiness.
    s = str_literal * 5
    assert type(s) == builtins.str

    s = str_literal * UntrustedInt(5)
    assert type(s) == builtins.str

    s = UntrustedInt(5) * str_literal
    assert type(s) == builtins.str

    # __sizeof__
    l = base_str.__sizeof__()
    assert type(l) == int

    l = untrusted_str.__sizeof__()
    assert type(l) == UntrustedInt
    assert l.synthesized is False

    l = synthesized_str.__sizeof__()
    assert type(l) == UntrustedInt
    assert l.synthesized is True

    # FIXME: str_literal returns builtins int
    l = str_literal.__sizeof__()
    assert type(l) == builtins.int

    # int() (Note that string object per se does not have __int__)
    s = UntrustedStr("10")
    try:
        int(s)
    except TypeError as e:
        print("'10' is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(s.to_trusted()) == 10
    assert type(int(s.to_trusted())) == int

    s = UntrustedStr("10", synthesized=True)
    try:
        int(s)
    except TypeError as e:
        print("'10' is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(s.to_trusted(forced=True)) == 10
    assert type(int(s.to_trusted(forced=True))) == int

    # FIXME: IMPORTANT NOTE ===============================================
    #  Python always cast int() to type int. When the calling object
    #  is an str literal, there is no interposition from our framework,
    #  but because the built-in int is shadowed by our own int, Python
    #  ensures return value to be our int.
    assert type(int(str("10"))) == int
    assert type(int("10")) == int

    # float() is similar to int()

    # str()
    try:
        str(untrusted_str)
    except TypeError as e:
        print("'Untrusted World!' is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_str.to_trusted() == 'untrusted'
    assert type(untrusted_str.to_trusted()) == str
    assert type(str(str_literal)) == str


def bytearray_test():
    b = bytearray([110, 115, 120, 125, 130])
    untrusted_b = UntrustedBytearray(b)
    assert type(untrusted_b) == UntrustedBytearray
    assert b == untrusted_b
    # Constructing a trust-aware bytearray with untrusted values returns an untrusted bytearray
    untrusted_b = bytearray([UntrustedInt(110), 111, 112, UntrustedInt(113, synthesized=True), 114])

    # append()
    b.append(135)
    assert type(b) == bytearray
    b.append(UntrustedInt(135))
    assert type(b) == UntrustedBytearray
    assert b.synthesized is False
    b = bytearray([110, 115, 120, 125, 130])
    b.append(UntrustedInt(135, synthesized=True))
    assert type(b) == UntrustedBytearray
    assert b.synthesized is True

    # capitalize()
    b = bytearray([110, 115, 120, 125, 130])
    b = b.capitalize()
    assert type(b) == bytearray
    untrusted_b = untrusted_b.capitalize()
    assert type(untrusted_b) == UntrustedBytearray

    # center()
    c = b.center(10)
    assert type(c) == bytearray
    c = b.center(UntrustedInt(10, synthesized=True))
    assert type(c) == UntrustedBytearray
    assert c.synthesized is True

    # clear()
    b.clear()
    assert type(b) == bytearray
    untrusted_b.clear()
    assert type(untrusted_b) == UntrustedBytearray

    # copy()
    b = bytearray([110, 115, 120, 125, 130])
    untrusted_b = UntrustedBytearray(b)
    c = b.copy()
    assert type(c) == bytearray
    c = untrusted_b.copy()
    assert type(c) == UntrustedBytearray
    assert c.synthesized is False

    # count()
    c = b.count(110)
    assert type(c) == int
    c = untrusted_b.count(115)
    assert type(c) == UntrustedInt
    c = b.count(UntrustedInt(100))
    assert type(c) == UntrustedInt
    assert c.synthesized is False

    # decode()
    b = bytearray([110, 111, 112, 113, 114])
    s = b.decode("ascii")
    assert type(s) == str
    untrusted_b = UntrustedBytearray(b)
    s = untrusted_b.decode("ascii")
    assert type(s) == UntrustedStr
    assert s.synthesized is False

    # We skip testing methods that are identical to those in str:
    # expandtabs(), find(), index(), join(), ljust(), lower(), lstrip(), maketrans(), partition(),
    # We also skip testing methods that return a boolean value:
    # endswith(), isalnum(), isalpha(), isascii(), isdigit(), islower(), isspace(), istitle(), isupper()

    # extend()
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b)
    b.extend(untrusted_b)
    assert type(b) == UntrustedBytearray

    # fromhex()
    b = bytearray.fromhex('B9 01EF')
    assert type(b) == bytearray
    b = UntrustedBytearray.fromhex('B9 01EF')
    assert type(b) == UntrustedBytearray
    b = bytearray.fromhex(UntrustedStr('B9 01EF', synthesized=True))
    assert type(b) == UntrustedBytearray
    assert b.synthesized is True

    # hex()
    b = bytearray([0xb9, 0x01, 0xef])
    h = b.hex()
    assert type(h) == str
    b = UntrustedBytearray([0xb9, 0x01, 0xef])
    h = b.hex()
    assert type(h) == UntrustedStr
    assert b.synthesized is False

    # insert()
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b)
    b.insert(2, 113)
    assert type(b) == bytearray
    b.insert(3, UntrustedInt(113))
    assert type(b) == UntrustedBytearray
    assert b.synthesized is False
    b.insert(3, UntrustedInt(113, synthesized=True))
    assert type(b) == UntrustedBytearray
    assert b.synthesized is True
    untrusted_b.insert(0, UntrustedInt(110, synthesized=True))
    assert type(untrusted_b) == UntrustedBytearray
    assert untrusted_b.synthesized is True

    # Only test some other methods that are likely to behave differently than the existing ones already tested.
    # pop()
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b, synthesized=True)
    e = b.pop(3)
    assert type(e) == int
    e = untrusted_b.pop(3)
    assert type(e) == UntrustedInt
    assert e.synthesized is True

    # __getitem__
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b, synthesized=True)
    assert type(b[3]) == int
    assert type(untrusted_b[3]) == UntrustedInt
    assert untrusted_b[3].synthesized is True

    # __iadd__
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b, synthesized=True)
    b += untrusted_b
    assert type(b) == UntrustedBytearray
    assert b.synthesized is True

    # __iter__
    b = bytearray([110, 111, 112, 113, 114])
    for i in b:
        assert type(i) == int
    untrusted_b = UntrustedBytearray(b, synthesized=True)
    for i in untrusted_b:
        assert type(i) == UntrustedInt
        assert i.synthesized is True

    # __len__
    b = bytearray([110, 111, 112, 113, 114])
    assert len(b) == 5
    assert type(len(b)) == int
    untrusted_b = UntrustedBytearray(b, synthesized=True)
    assert len(untrusted_b) == 5
    assert type(len(untrusted_b)) == UntrustedInt

    # __setitem__
    b = bytearray([110, 111, 112, 113, 114])
    untrusted_b = UntrustedBytearray(b)
    b[3] = UntrustedInt(113, synthesized=True)
    assert type(b) == UntrustedBytearray
    assert b.synthesized is True


# TODO: not thoroughly tested
def decimal_test():
    base_decimal = Decimal('3.14')
    # Make sure UntrustedDecimal can take all forms acceptable by Decimal
    untrusted_decimal_1 = UntrustedDecimal('3.14')  # string input
    untrusted_decimal_2 = UntrustedDecimal((0, (3, 1, 4), -2))  # tuple (sign, digit_tuple, exponent)
    assert untrusted_decimal_2 == Decimal((0, (3, 1, 4), -2))
    assert type(untrusted_decimal_2) is UntrustedDecimal
    untrusted_decimal_3 = UntrustedDecimal(Decimal(314))  # another decimal instance
    assert untrusted_decimal_3 == Decimal(Decimal(314))
    assert type(untrusted_decimal_3) is UntrustedDecimal
    untrusted_decimal_4 = UntrustedDecimal('  3.14 \n')  # leading and trailing whitespace is okay
    assert untrusted_decimal_4 == Decimal('  3.14 \n')
    assert type(untrusted_decimal_4) is UntrustedDecimal
    untrusted_decimal_5 = UntrustedDecimal(314)  # int
    assert untrusted_decimal_5 == Decimal(314)
    assert type(untrusted_decimal_5) is UntrustedDecimal
    synthesized_decimal_1 = UntrustedDecimal('3.14', synthesized=True)

    d = base_decimal + untrusted_decimal_1
    assert d == base_decimal + base_decimal
    assert type(d) == UntrustedDecimal
    assert d.synthesized is False

    d = base_decimal * untrusted_decimal_1
    assert d == base_decimal * base_decimal
    assert type(d) == UntrustedDecimal
    assert d.synthesized is False

    d = base_decimal * synthesized_decimal_1
    assert d == base_decimal * base_decimal
    assert type(d) == UntrustedDecimal
    assert d.synthesized is True

    d = UntrustedDecimal(10)
    try:
        int(d)
    except TypeError as e:
        print("10 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert d.to_trusted() == 10

    d = UntrustedDecimal(10, synthesized=True)
    try:
        int(d)
    except TypeError as e:
        print("10 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))

    try:
        float(synthesized_decimal_1)
    except TypeError as e:
        print("3.14 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))

    d = UntrustedDecimal(9.8596, synthesized=True)
    try:
        float(d)
    except TypeError as e:
        print("9.8596 is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert d.to_trusted(forced=True) == d
    assert type(float(d.to_trusted(forced=True))) == float

    try:
        str(d)
    except TypeError as e:
        print("9.8596 is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))

    try:
        str(synthesized_decimal_1)
    except TypeError as e:
        print("3.14 is synthesized, converting it to str using str() results in "
              "error: {error}".format(error=e))


if __name__ == "__main__":
    import math
    import builtins
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from django.splice.archive.trustedtypes import TrustAwareInt as int
    from django.splice.archive.trustedtypes import TrustAwareFloat as float
    from django.splice.archive.trustedtypes import TrustAwareStr as str
    from django.splice.archive.trustedtypes import TrustAwareBytes as bytes
    from django.splice.archive.trustedtypes import TrustAwareBytearray as bytearray
    from django.splice.archive.trustedtypes import TrustAwareDecimal as Decimal
    # Import from this file to fix the namespace issue. Reference:
    # https://stackoverflow.com/questions/15159854/python-namespace-main-class-not-isinstance-of-package-class
    from django.splice.archive.untrustedtypes import (UntrustedInt, UntrustedFloat, UntrustedStr, UntrustedBytes,
                                                      UntrustedBytearray, UntrustedDecimal)

    int_test()
    float_test()
    str_test()
    bytearray_test()
    decimal_test()
