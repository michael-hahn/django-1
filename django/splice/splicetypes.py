"""Splice classes."""

from decimal import Decimal
from datetime import datetime

from django.splice.splice import SpliceMixin


class SpliceInt(SpliceMixin, int):
    """
    Subclass Python trusted int class and SpliceMixin.
    Note that "trusted" and "synthesized" are *keyed*
    parameters. Construct a trusted int value by default.
    """
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
        return self._splice_hash_()

    def _splice_hash_(self):
        """Called by __hash__() but return a decorated value."""
        return type(self).custom_hash(self)

    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return cls(value, trusted=trusted, synthesized=synthesized)


class SpliceFloat(SpliceMixin, float):
    """Subclass Python trusted float class and SpliceMixin."""
    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return cls(value, trusted=trusted, synthesized=synthesized)


class SpliceStr(SpliceMixin, str):
    """Subclass Python trusted str class and SpliceMixin."""
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
        return self._splice_hash_()

    def _splice_hash_(self):
        """Called by __hash__() but return a decorated value."""
        chars = bytes(self, 'ascii')
        return type(self).custom_hash(chars)

    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return cls(value, trusted=trusted, synthesized=synthesized)

    def __radd__(self, other):
        """Define __radd__ so a str literal + an untrusted str returns an untrusted str."""
        trusted = self.trusted
        synthesized = self.synthesized
        if isinstance(other, SpliceMixin):
            synthesized |= other.synthesized
            trusted |= other.trusted
        return SpliceStr(other.__add__(self), trusted=trusted, synthesized=synthesized)


class SpliceBytes(SpliceMixin, bytes):
    """Subclass Python builtin bytes class and SpliceMixin."""
    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return SpliceBytes(value, trusted=trusted, synthesized=synthesized)


class SpliceBytearray(SpliceMixin, bytearray):
    """Subclass Python builtin bytearray class and SpliceMixin."""
    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return SpliceBytearray(value, trusted=trusted, synthesized=synthesized)


class SpliceDecimal(SpliceMixin, Decimal):
    """Subclass Python decimal module's Decimal class and SpliceMixin."""
    @classmethod
    def splicify(cls, value, trusted, synthesized):
        return SpliceDecimal(value, trusted=trusted, synthesized=synthesized)


class SpliceDatetime(SpliceMixin, datetime):
    """
    Subclass Python datetime module's datetime class and SpliceMixin.
    This is an example to showcase it's easy to create a splice-aware
    class from an existing Python class.
    """

    @classmethod
    def splicify(cls, value, trusted, synthesized):
        year = value.year
        month = value.month
        day = value.day
        hour = value.hour
        minute = value.minute
        second = value.second
        microsecond = value.microsecond
        return SpliceDatetime(year=year,
                              month=month,
                              day=day,
                              hour=hour,
                              minute=minute,
                              second=second,
                              microsecond=microsecond,
                              trusted=trusted,
                              synthesized=synthesized)


if __name__ == "__main__":
    # d = SpliceDatetime(year=2020, month=12, day=24)
    from django.splice.splicetypes import SpliceInt as int

    i = int("20", trusted=False, synthesized=True)
    print(i.trusted)
    print(i.synthesized)
    s = SpliceStr("20")
    print(s.trusted)

    print(s.synthesized)
    i = int(s)
    # i = int(s)
    print(i)
    print(type(i))
    print(i.trusted)
    # i = SpliceInt(10)
    # f = float(i)
