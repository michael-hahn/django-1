import pytest
import builtins
import math
from django.splice.splicetypes import SpliceInt as int
from django.splice.splicetypes import SpliceFloat as float
from django.splice.splicetypes import SpliceStr as str
from django.splice.splicetypes import SpliceBytes as bytes


@pytest.fixture()
def trusted_int():
    return int("A", base=16)


@pytest.fixture()
def untrusted_int():
    return int(10, trusted=False)


@pytest.fixture()
def synthesized_int():
    return int(10, trusted=False, synthesized=True)


@pytest.fixture()
def literal_int():
    return 10


def test_as_integer_ratio(trusted_int, untrusted_int, synthesized_int, literal_int):
    r_x, r_y = trusted_int.as_integer_ratio()
    assert r_x == 10
    assert r_y == 1
    assert type(r_x) == int
    assert type(r_y) == int
    assert r_x.trusted is True
    assert r_x.synthesized is False
    assert r_x.trusted is True
    assert r_y.synthesized is False

    r_x, r_y = untrusted_int.as_integer_ratio()
    assert r_x == 10
    assert r_y == 1
    assert type(r_x) == int
    assert type(r_y) == int
    assert r_x.trusted is False
    assert r_x.synthesized is False
    assert r_x.trusted is False
    assert r_y.synthesized is False

    r_x, r_y = synthesized_int.as_integer_ratio()
    assert r_x == 10
    assert r_y == 1
    assert type(r_x) == int
    assert type(r_y) == int
    assert r_x.trusted is False
    assert r_x.synthesized is True
    assert r_x.trusted is False
    assert r_y.synthesized is True

    # FIXME: int_literal returns builtins int
    r_x, r_y = literal_int.as_integer_ratio()
    assert r_x == 10
    assert r_y == 1
    assert type(r_x) == builtins.int
    assert type(r_y) == builtins.int


def test_bit_length(trusted_int, untrusted_int, synthesized_int, literal_int):
    bl = trusted_int.bit_length()
    assert bl == 4
    assert type(bl) == int
    assert bl.trusted is True
    assert bl.synthesized is False

    bl = untrusted_int.bit_length()
    assert bl == 4
    assert type(bl) == int
    assert bl.trusted is False
    assert bl.synthesized is False

    bl = synthesized_int.bit_length()
    assert bl == 4
    assert type(bl) == int
    assert bl.trusted is False
    assert bl.synthesized is True

    # FIXME: int_literal returns builtins int
    bl = literal_int.bit_length()
    assert bl == 4
    assert type(bl) == builtins.int


def test_conjugate(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = trusted_int.conjugate()
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = untrusted_int.conjugate()
    assert i == untrusted_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = synthesized_int.conjugate()
    assert i == synthesized_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    # FIXME: int_literal returns builtins int
    i = literal_int.conjugate()
    assert i == literal_int
    assert type(i) == builtins.int


def test_from_bytes(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = int.from_bytes([1, 3, 4], byteorder='big')
    assert i == 66308
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = int.from_bytes([1, int(3, trusted=False, synthesized=True), 4], byteorder='big')
    assert i == 66308
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = int.from_bytes([int(1, trusted=False, synthesized=False), 3, 4], byteorder='big')
    assert i == 66308
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False


def test_to_bytes(trusted_int, untrusted_int, synthesized_int, literal_int):
    b = trusted_int.to_bytes(10, 'big')
    assert type(b) == bytes
    assert b.trusted is True
    assert b.synthesized is False

    b = untrusted_int.to_bytes(10, 'big')
    assert type(b) == bytes
    assert b.trusted is False
    assert b.synthesized is False

    b = synthesized_int.to_bytes(10, 'big')
    assert type(b) == bytes
    assert b.trusted is False
    assert b.synthesized is True

    # FIXME: int_literal returns builtins int
    b = literal_int.to_bytes(10, 'big')
    assert type(b) == builtins.bytes


def test_abs(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = abs(-trusted_int)
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = (-trusted_int).__abs__()
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = abs(-untrusted_int)
    assert i == untrusted_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = (-untrusted_int).__abs__()
    assert i == untrusted_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = abs(-synthesized_int)
    assert i == synthesized_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = (-synthesized_int).__abs__()
    assert i == synthesized_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    # FIXME: int_literal returns builtins int
    i = abs(-literal_int)
    assert i == literal_int
    assert type(i) == builtins.int

    i = (-literal_int).__abs__()
    assert i == literal_int
    assert type(i) == builtins.int


def test_add(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = trusted_int + trusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = trusted_int.__add__(trusted_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = trusted_int + untrusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = trusted_int.__add__(untrusted_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = trusted_int + literal_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = trusted_int.__add__(literal_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = untrusted_int + trusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = untrusted_int.__add__(trusted_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = untrusted_int + literal_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = untrusted_int.__add__(literal_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = synthesized_int + untrusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int.__add__(untrusted_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int + literal_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int.__add__(literal_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int + trusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int.__add__(trusted_int)
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = literal_int + untrusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    # FIXME: int_literal works only with reflected methods (above), not with directly calling special method (below)
    i = literal_int.__add__(untrusted_int)
    assert i == 20
    assert type(i) == builtins.int

    i = literal_int + synthesized_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = literal_int.__add__(synthesized_int)
    assert i == 20
    assert type(i) == builtins.int

    i = literal_int + trusted_int
    assert i == 20
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = literal_int.__add__(trusted_int)
    assert i == 20
    assert type(i) == builtins.int
# Other binary arithmetic operations similar to + (__add__) are skipped:
# & (__and__), | (__or__), // (__floordiv__), << (__lshift__), % (__mod__)
# * (__mul__), ** (__pow__), >> (__rshift__), - (__sub__), ^ (__xor__)


# FIXME: bool (__bool__) always returns bool
def test_bool(trusted_int, untrusted_int, synthesized_int, literal_int):
    b = bool(trusted_int)
    assert b is True
    assert type(b) == bool

    b = bool(untrusted_int)
    assert b is True
    assert type(b) == bool

    b = bool(synthesized_int)
    assert b is True
    assert type(b) == bool

    b = bool(literal_int)
    assert b is True
    assert type(b) == bool
# Other bool operations are skipped:
# == (__eq__), >= (__ge__), > (__gt__), <= (__le__), < (__lt__), != (__ne__)


def test_ceil(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = math.ceil(trusted_int)
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = math.ceil(untrusted_int)
    assert i == untrusted_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = math.ceil(synthesized_int)
    assert i == synthesized_int
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    # FIXME: int_literal returns builtins int
    i = math.ceil(literal_int)
    assert i == literal_int
    assert type(i) == builtins.int
# Other similar math operations are skipped:
# floor() (__floor__), trunc() (__trunc__)


def test_divmod(trusted_int, untrusted_int, synthesized_int, literal_int):
    d_x, d_y = divmod(trusted_int, 4)
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int
    assert d_x.trusted is True
    assert d_x.synthesized is False
    assert d_y.trusted is True
    assert d_y.synthesized is False

    d_x, d_y = divmod(10, int(4))
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int
    assert d_x.trusted is True
    assert d_x.synthesized is False
    assert d_y.trusted is True
    assert d_y.synthesized is False

    d_x, d_y = divmod(untrusted_int, 4)
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int
    assert d_x.trusted is False
    assert d_x.synthesized is False
    assert d_y.trusted is False
    assert d_y.synthesized is False

    d_x, d_y = divmod(synthesized_int, 4)
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int
    assert d_x.trusted is False
    assert d_x.synthesized is True
    assert d_y.trusted is False
    assert d_y.synthesized is True

    d_x, d_y = divmod(literal_int, int(4))
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == int
    assert type(d_y) == int
    assert d_x.trusted is True
    assert d_x.synthesized is False
    assert d_y.trusted is True
    assert d_y.synthesized is False

    # FIXME: int_literal works only with reflected methods (above), not with directly calling special method (below)
    d_x, d_y = literal_int.__divmod__(int(4))
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == builtins.int
    assert type(d_y) == builtins.int

    # FIXME: int_literal returns builtins int
    d_x, d_y = divmod(literal_int, 4)
    assert d_x == 2
    assert d_y == 2
    assert type(d_x) == builtins.int
    assert type(d_y) == builtins.int


def test_float(trusted_int, untrusted_int, synthesized_int, literal_int):
    f = float(untrusted_int)
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False
    assert untrusted_int.to_trusted() == 10
    assert type(float(untrusted_int)) == float

    untrusted_int = int(10, trusted=False, synthesized=False)
    f = untrusted_int.__float__()
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False
    assert type(untrusted_int.to_trusted().__float__()) == float

    f = float(synthesized_int)
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True
    assert synthesized_int.to_trusted(forced=True) == 10
    assert type(float(synthesized_int)) == float

    synthesized_int = int(10, trusted=False, synthesized=True)
    f = synthesized_int.__float__()
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True
    assert type(synthesized_int.to_trusted(forced=True).__float__()) == float

    assert float(trusted_int) == 10
    assert type(float(trusted_int)) == float

    assert trusted_int.__float__() == 10
    assert type(trusted_int.__float__()) == float

    # FIXME: Python always cast float() to type float. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in float is shadowed by our own float, Python
    #  ensures return value to be our float. However, the same enforcement
    #  does not apply when __float__ is called directly from an int literal
    assert float(literal_int) == 10
    assert type(float(literal_int)) == float

    assert literal_int.__float__() == 10
    assert type(literal_int.__float__()) == builtins.float


def test_format(trusted_int, untrusted_int, synthesized_int, literal_int):
    with pytest.raises(TypeError) as excinfo:
        "{}".format(untrusted_int)
    assert "cannot use format() or __format__" in str(excinfo.value)
    s = untrusted_int.to_trusted()
    assert type(format(s)) == str

    with pytest.raises(TypeError) as excinfo:
        "{}".format(synthesized_int)
    assert "cannot use format() or __format__" in str(excinfo.value)
    s = synthesized_int.to_trusted(forced=True)
    assert type(format(s)) == str

    s = format(trusted_int)
    assert type(s) == str

    # FIXME: int_literal format() returns builtins str
    s = format(literal_int)
    assert type(s) == builtins.str


def test_hash(trusted_int, untrusted_int, synthesized_int, literal_int):
    h = hash(untrusted_int)
    assert type(h) == int
    assert h.trusted is False
    assert h.synthesized is False

    h = untrusted_int.__hash__()
    assert type(h) == int
    assert h.trusted is False
    assert h.synthesized is False

    h = hash(synthesized_int)
    assert type(h) == int
    assert h.trusted is False
    assert h.synthesized is True

    h = synthesized_int.__hash__()
    assert type(h) == int
    assert h.trusted is False
    assert h.synthesized is True

    h = hash(trusted_int)
    assert type(h) == int
    assert h.trusted is True
    assert h.synthesized is False

    h = trusted_int.__hash__()
    assert type(h) == int
    assert h.trusted is True
    assert h.synthesized is False

    # FIXME: int_literal returns builtins int
    h = hash(literal_int)
    assert type(h) == builtins.int

    h = literal_int.__hash__()
    assert type(h) == builtins.int


def test_index(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = untrusted_int.__index__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = synthesized_int.__index__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = trusted_int.__index__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    # FIXME: int_literal returns builtins int
    i = literal_int.__index__()
    assert i == 10
    assert type(i) == builtins.int


def test_int(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = int(untrusted_int)
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False
    assert untrusted_int.to_trusted() == 10
    assert type(int(untrusted_int.to_trusted())) == int

    untrusted_int = int(10, trusted=False, synthesized=False)

    i = untrusted_int.__int__()
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False
    assert untrusted_int.to_trusted() == 10
    assert type(untrusted_int.to_trusted().__int__()) == int

    i = int(synthesized_int)
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True
    assert synthesized_int.to_trusted(forced=True) == 10
    assert type(synthesized_int.__int__()) == int

    synthesized_int = int(10, trusted=False, synthesized=True)
    i = synthesized_int.__int__()
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True
    assert type(synthesized_int.to_trusted(forced=True).__int__()) == int

    i = int(trusted_int)
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False
    i = trusted_int.__int__()
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    # FIXME: Python always cast int() to type int. When the calling object
    #  is an int literal, there is no interposition from our framework, but
    #  because the built-in int is shadowed by our own float, Python ensures
    #  return value to be our int. However, the same enforcement does not
    #  apply when __int__ is called directly from an int literal!
    i = int(literal_int)
    assert i == trusted_int
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False
    i = literal_int.__int__()
    assert i == trusted_int
    assert type(i) == builtins.int


def test_invert(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = ~untrusted_int
    assert i == -11
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = untrusted_int.__invert__()
    assert i == -11
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = ~synthesized_int
    assert i == -11
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int.__invert__()
    assert i == -11
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = ~trusted_int
    assert i == -11
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = trusted_int.__invert__()
    assert i == -11
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    # FIXME: int_literal returns builtins int
    i = ~literal_int
    assert i == -11
    assert type(i) == builtins.int

    i = literal_int.__invert__()
    assert i == -11
    assert type(i) == builtins.int
# Other binary arithmetic operations similar to ~ (__invert__) are skipped:
# - (__neg__), + (__pos__)

# All reflected (swapped) methods are skipped since we have tested them in non-reflected methods:
# __radd__, __rand__, __rdivmod__, __rfloordiv__, __rlshift__, __rmod__, __rmul__,
# __ror__, __rpow__, __rrshift__, __rsub__, __rtruediv__, __rxor__


def test_repr(trusted_int, untrusted_int, synthesized_int, literal_int):
    with pytest.raises(TypeError) as excinfo:
        repr(untrusted_int)
    assert "cannot use repr() or __repr__" in str(excinfo.value)
    s = untrusted_int.to_trusted()
    assert type(repr(s)) == str

    with pytest.raises(TypeError) as excinfo:
        repr(synthesized_int)
    assert "cannot use repr() or __repr__" in str(excinfo.value)
    s = synthesized_int.to_trusted(forced=True)
    assert type(repr(s)) == str

    s = repr(trusted_int)
    assert type(s) == str

    # FIXME: int_literal format() returns builtins str
    s = repr(literal_int)
    assert type(s) == builtins.str


def test_round(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = round(untrusted_int)
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = untrusted_int.__round__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = round(synthesized_int)
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = synthesized_int.__round__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = round(trusted_int)
    assert i == 10
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    i = trusted_int.__round__()
    assert i == 10
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    # FIXME: int_literal returns builtins int
    i = round(literal_int)
    assert i == 10
    assert type(i) == builtins.int

    i = literal_int.__round__()
    assert i == 10
    assert type(i) == builtins.int


def test_sizeof(trusted_int, untrusted_int, synthesized_int, literal_int):
    i = untrusted_int.__sizeof__()
    assert i == 28
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False

    i = synthesized_int.__sizeof__()
    assert i == 28
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True

    i = trusted_int.__sizeof__()
    assert i == 28
    assert type(i) == int
    assert i.trusted is True
    assert i.synthesized is False

    # FIXME: int_literal returns builtins int
    i = literal_int.__sizeof__()
    assert i == 28
    assert type(i) == builtins.int


def test_truediv(trusted_int, untrusted_int, synthesized_int, literal_int):
    f = untrusted_int / 4
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False

    f = untrusted_int.__truediv__(4)
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False

    f = 4 / untrusted_int
    assert f == 2/5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False

    f = synthesized_int / 4
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True

    f = synthesized_int.__truediv__(4)
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True

    f = 4 / synthesized_int
    assert f == 2 / 5
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True

    f = trusted_int / 4
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is True
    assert f.synthesized is False

    f = trusted_int.__truediv__(4)
    assert f == 2.5
    assert type(f) == float
    assert f.trusted is True
    assert f.synthesized is False

    f = 4 / trusted_int
    assert f == 2 / 5
    assert type(f) == float
    assert f.trusted is True
    assert f.synthesized is False

    # FIXME: int_literal returns builtins float
    f = literal_int.__truediv__(untrusted_int)
    assert f == 1
    assert type(f) == builtins.float

    f = literal_int.__truediv__(synthesized_int)
    assert f == 1
    assert type(f) == builtins.float

    f = literal_int.__truediv__(trusted_int)
    assert f == 1
    assert type(f) == builtins.float

    i = literal_int / 12
    assert i == 5/6
    assert type(i) == builtins.float


def test_str(trusted_int, untrusted_int, synthesized_int, literal_int):
    with pytest.raises(TypeError) as excinfo:
        str(untrusted_int)
    assert "cannot use str() or __str__" in str(excinfo.value)
    untrusted_int.to_trusted()
    assert str(untrusted_int) == "10"
    assert type(str(untrusted_int)) == str

    with pytest.raises(TypeError) as excinfo:
        str(synthesized_int)
    assert "cannot use str() or __str__" in str(excinfo.value)
    synthesized_int.to_trusted(forced=True)
    assert str(synthesized_int) == "10"
    assert type(str(synthesized_int)) == str

    s = str(trusted_int)
    assert s == "10"
    assert type(s) == str

    # FIXME: Python always cast str() to type str. When the calling object
    #  is an int literal, there is no interposition from our framework,
    #  but because the built-in str is shadowed by our own str, Python
    #  ensures return value to be our str. However, the same enforcement
    #  does not apply when __str__ is called directly from an int literal
    s = str(literal_int)
    assert s == "10"
    assert type(s) == str

    assert literal_int.__str__() == "10"
    assert type(literal_int.__str__()) == builtins.str
