import pytest
from django.splice.splicetypes import SpliceDatetime as datetime
from django.splice.splicetypes import SpliceFloat as float
from django.splice.splicetypes import SpliceStr as str


@pytest.fixture()
def trusted_datetime():
    return datetime(year=2020, month=12, day=13, hour=23)


@pytest.fixture()
def untrusted_datetime():
    return datetime(year=2020, month=12, day=13, hour=23, trusted=False)


@pytest.fixture()
def synthesized_datetime():
    return datetime(year=2020, month=12, day=13, hour=23, trusted=False, synthesized=True)


def test_fromtimestamp():
    d = datetime.fromtimestamp(123456)
    assert type(d) == datetime
    assert d.trusted is True
    assert d.synthesized is False

    d = datetime.fromtimestamp(float(123456, trusted=False))
    assert type(d) == datetime
    assert d.trusted is False
    assert d.synthesized is False

    d = datetime.fromtimestamp(float(123456, trusted=False, synthesized=True))
    assert type(d) == datetime
    assert d.trusted is False
    assert d.synthesized is True


def test_stamp(trusted_datetime, untrusted_datetime, synthesized_datetime):
    f = trusted_datetime.timestamp()
    assert type(f) == float
    assert f.trusted is True
    assert f.synthesized is False

    f = untrusted_datetime.timestamp()
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is False

    f = synthesized_datetime.timestamp()
    assert type(f) == float
    assert f.trusted is False
    assert f.synthesized is True


def test_ctime(trusted_datetime, untrusted_datetime, synthesized_datetime):
    s = trusted_datetime.ctime()
    assert type(s) == str
    assert s.trusted is True
    assert s.synthesized is False

    s = untrusted_datetime.ctime()
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is False

    s = synthesized_datetime.ctime()
    assert type(s) == str
    assert s.trusted is False
    assert s.synthesized is True
