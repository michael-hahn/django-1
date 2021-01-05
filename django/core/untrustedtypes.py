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

    def __add__(self, other):
        res = super().__add__(other)
        # result is untrusted if at least one operand is untrusted
        untrusted = self.untrusted or other.untrusted
        # result is synthesized if at least one operand is synthesized
        synthesized = self.synthesized or other.synthesized
        return self.__class__(res, untrusted=untrusted, synthesized=synthesized)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "UntrustedInt(%d)" % int(self)
