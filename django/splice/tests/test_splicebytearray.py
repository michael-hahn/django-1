import pytest
from django.splice.splicetypes import SpliceInt as int
from django.splice.splicetypes import SpliceBytearray as bytearray


@pytest.fixture()
def trusted_bytearray():
    return bytearray([110, 115, 120, 125, 130])


@pytest.fixture()
def untrusted_bytearray():
    return bytearray([110, 115, 120, 125, 130], trusted=False, synthesized=False)


@pytest.fixture()
def synthesized_bytearray():
    return bytearray([110, 115, 120, 125, 130], trusted=False, synthesized=True)


def test_append(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    trusted_bytearray.append(135)
    assert type(trusted_bytearray) == bytearray
    assert trusted_bytearray.trusted is True
    assert trusted_bytearray.synthesized is False

    trusted_bytearray.append(int(135, trusted=False, synthesized=False))
    assert type(trusted_bytearray) == bytearray
    assert trusted_bytearray.trusted is False
    assert trusted_bytearray.synthesized is False

    trusted_bytearray = bytearray([110, 115, 120, 125, 130])
    trusted_bytearray.append(int(135, trusted=False, synthesized=True))
    assert type(trusted_bytearray) == bytearray
    assert trusted_bytearray.trusted is False
    assert trusted_bytearray.synthesized is True


def test_capitalize(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    b = trusted_bytearray.capitalize()
    assert type(b) == bytearray
    assert b.trusted is True
    assert b.synthesized is False

    b = untrusted_bytearray.capitalize()
    assert type(b) == bytearray
    assert b.trusted is False
    assert b.synthesized is False

    b = synthesized_bytearray.capitalize()
    assert type(b) == bytearray
    assert b.trusted is False
    assert b.synthesized is True


def test_getitem(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    b = trusted_bytearray[0]
    assert type(b) == int
    assert b.trusted is True
    assert b.synthesized is False

    b = untrusted_bytearray[0]
    assert type(b) == int
    assert b.trusted is False
    assert b.synthesized is False

    b = synthesized_bytearray[0]
    assert type(b) == int
    assert b.trusted is False
    assert b.synthesized is True


def test_iter(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    for i in trusted_bytearray:
        assert type(i) == int
        assert i.trusted is True
        assert i.synthesized is False
    for i in untrusted_bytearray:
        assert type(i) == int
        assert i.trusted is False
        assert i.synthesized is False
    for i in synthesized_bytearray:
        assert type(i) == int
        assert i.trusted is False
        assert i.synthesized is True


def test_len(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    l = len(trusted_bytearray)
    assert l == 5
    assert type(l) == int
    assert l.trusted is True
    assert l.synthesized is False

    l = len(untrusted_bytearray)
    assert l == 5
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is False

    l = len(synthesized_bytearray)
    assert l == 5
    assert type(l) == int
    assert l.trusted is False
    assert l.synthesized is True


def test_setitem(trusted_bytearray, untrusted_bytearray, synthesized_bytearray):
    trusted_bytearray[3] = int(113, trusted=False, synthesized=True)
    assert type(trusted_bytearray) == bytearray
    assert trusted_bytearray.trusted is False
    assert trusted_bytearray.synthesized is True

    untrusted_bytearray[3] = int(113, trusted=False, synthesized=True)
    assert type(untrusted_bytearray) == bytearray
    assert trusted_bytearray.trusted is False
    assert trusted_bytearray.synthesized is True
