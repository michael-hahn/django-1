import pytest
import builtins
from django.splice.splicetypes import SpliceInt as int
from django.splice.splicetypes import SpliceFloat as float
from django.splice.splicetypes import SpliceStr as str
from django.splice.splicetypes import SpliceBytes as bytes


@pytest.fixture()
def trusted_str():
    return str("Hello")


@pytest.fixture()
def untrusted_str():
    return str("untrusted", trusted=False, synthesized=False)


@pytest.fixture()
def synthesized_str():
    return str("synthesized", trusted=False, synthesized=True)


@pytest.fixture()
def literal_str():
    return "World"


def test_capitalize(trusted_str, untrusted_str, synthesized_str, literal_str):
    s = trusted_str.capitalize()
    assert s == "Hello"
    assert type(s) == str
    assert s.trusted is True
    assert s.synthesized is False

    s = untrusted_str.capitalize()
    assert s == "Untrusted"
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is False

    s = synthesized_str.capitalize()
    assert s == "Synthesized"
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is True

    # FIXME: str_literal returns builtins str
    s = literal_str.capitalize()
    assert s == "World"
    assert type(s) == builtins.str


def test_count(trusted_str, untrusted_str, synthesized_str, literal_str):
    c = trusted_str.count("e")
    assert c == 1
    assert type(c) == int
    assert c.trusted is True
    assert c.synthesized is False

    c = trusted_str.count("e", int(0, trusted=False, synthesized=False))
    assert c == 1
    assert type(c) == int
    assert c.trusted is False
    assert c.synthesized is False

    c = trusted_str.count(str("e", trusted=False, synthesized=True))
    assert c == 1
    assert type(c) == int
    assert c.trusted is False
    assert c.synthesized is True

    c = untrusted_str.count("u")
    assert c == 2
    assert type(c) == int
    assert c.trusted is False
    assert c.synthesized is False

    c = untrusted_str.count("u", int(0, trusted=False, synthesized=True))
    assert c == 2
    assert type(c) == int
    assert c.trusted is False
    assert c.synthesized is True

    c = synthesized_str.count("s")
    assert c == 2
    assert type(c) == int
    assert c.trusted is False
    assert c.synthesized is True

    # FIXME: str_literal returns builtins int
    c = literal_str.count(str("d", trusted=False, synthesized=False))
    assert c == 1
    assert type(c) == builtins.int


def test_encode(trusted_str, untrusted_str, synthesized_str, literal_str):
    b = trusted_str.encode()
    assert type(b) == bytes
    assert b.trusted is True
    assert b.synthesized is False

    b = untrusted_str.encode()
    assert type(b) == bytes
    assert b.trusted is False
    assert b.synthesized is False

    b = synthesized_str.encode()
    assert type(b) == bytes
    assert b.trusted is False
    assert b.synthesized is True

    # FIXME: str_literal returns builtins bytes
    b = literal_str.encode()
    assert type(b) == builtins.bytes


def test_join(trusted_str, untrusted_str, synthesized_str, literal_str):
    base_s = str(".")
    s = base_s.join(["Hello", "world"])
    assert s == "Hello.world"
    assert type(s) == str
    assert s.trusted is True
    assert s.synthesized is False

    s = base_s.join(["Hello", str("world", trusted=False, synthesized=False)])
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is False
    assert s.to_trusted() == "Hello.world"

    s = base_s.join(["Hello", str("world", trusted=False, synthesized=True)])
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is True
    assert s.to_trusted(forced=True) == "Hello.world"

    untrusted_s = str(".", trusted=False, synthesized=False)
    s = untrusted_s.join(["Hello", str("world", trusted=False, synthesized=True)])
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is True
    assert s.to_trusted(forced=True) == "Hello.world"

    synthesized_s = str(".", trusted=False, synthesized=True)
    s = synthesized_s.join(["Hello", "world"])
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is True
    assert s.to_trusted(forced=True) == "Hello.world"

    # FIXME: str_literal returns builtins str
    s_literal = "."
    s = s_literal.join([str("Hello"), "world"])
    assert s == "Hello.world"
    assert type(s) == builtins.str

    s = s_literal.join([str("Hello", trusted=False, synthesized=False), "world"])
    assert s == "Hello.world"
    assert type(s) == builtins.str


def test_iter(trusted_str, untrusted_str, synthesized_str, literal_str):
    for s in trusted_str:
        assert type(s) == str
        assert s.trusted is True
        assert s.synthesized is False

    for s in untrusted_str:
        assert type(s) == str
        assert s.trusted is False
        assert s.synthesized is False

    for s in synthesized_str:
        assert type(s) == str
        assert s.trusted is False
        assert s.synthesized is True

    # FIXME: str_literal returns builtins str
    for s in literal_str:
        assert type(s) == builtins.str


def test_len(trusted_str, untrusted_str, synthesized_str, literal_str):
    l = len(trusted_str)
    assert l == 5
    assert type(l) == int
    assert l.trusted is True
    assert l.synthesized is False

    l = trusted_str.__len__()
    assert l == 5
    assert type(l) == int
    assert l.trusted is True
    assert l.synthesized is False

    l = len(untrusted_str)
    assert l == 9
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is False

    l = untrusted_str.__len__()
    assert l == 9
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is False

    l = len(synthesized_str)
    assert l == 11
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is True

    l = synthesized_str.__len__()
    assert l == 11
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is True

    # FIXME: str_literal returns builtins str
    l = len(literal_str)
    assert l == 5
    assert type(l) == builtins.int

    l = literal_str.__len__()
    assert l == 5
    assert type(l) == builtins.int


def test_int(trusted_str, untrusted_str, synthesized_str, literal_str):
    s = str("10", trusted=False, synthesized=False)
    i = int(s)
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is False
    assert int(s.to_trusted()) == 10
    assert type(int(s)) == int

    s = str("10", trusted=False, synthesized=True)
    i = int(s)
    assert type(i) == int
    assert i.trusted is False
    assert i.synthesized is True
    i = int(s.to_trusted(forced=True))
    assert i == 10
    assert type(i) == int

    # FIXME: Python always cast int() to type int. When the calling object
    #  is an str literal, there is no interposition from our framework,
    #  but because the built-in int is shadowed by our own int, Python
    #  ensures return value to be our int.
    assert type(int(str("10"))) == int
    assert type(int("10")) == int
