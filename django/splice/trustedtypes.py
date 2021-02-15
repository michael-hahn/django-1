"""Trust-aware classes."""

from decimal import Decimal
from datetime import datetime

from django.splice.utils import TrustAwareMixin, UntrustedMixin


class TrustAwareInt(TrustAwareMixin, int):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = super(UntrustedMixin, value).__int__()
        return TrustAwareInt(value)


class TrustAwareFloat(TrustAwareMixin, float):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = super(UntrustedMixin, value).__float__()
        return TrustAwareFloat(value)


class TrustAwareStr(TrustAwareMixin, str):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = super(UntrustedMixin, value).__str__()
        return TrustAwareStr(value)

    def __radd__(self, other):
        """Define __radd__ so a str literal + a trust aware str returns a trust aware str."""
        return TrustAwareStr(other.__add__(self))


class TrustAwareBytes(TrustAwareMixin, bytes):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = bytes(value)
        return TrustAwareBytes(value)


class TrustAwareBytearray(TrustAwareMixin, bytearray):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = bytearray(value)
        return TrustAwareBytearray(value)


class TrustAwareDecimal(TrustAwareMixin, Decimal):
    @classmethod
    def trustify(cls, value):
        if isinstance(value, UntrustedMixin):
            value = Decimal(value)
        return TrustAwareDecimal(value)


class TrustAwareDatetime(TrustAwareMixin, datetime):
    @classmethod
    def trustify(cls, value):
        year = value.year
        month = value.month
        day = value.day
        hour = value.hour
        minute = value.minute
        second = value.second
        microsecond = value.microsecond
        return TrustAwareDatetime(year=year,
                                  month=month,
                                  day=day,
                                  hour=hour,
                                  minute=minute,
                                  second=second,
                                  microsecond=microsecond)


if __name__ == "__main__":
    pass
