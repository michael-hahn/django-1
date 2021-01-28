"""
Untrusted classes
"""
from collections import UserString
from decimal import Decimal

import inspect
import functools
import warnings


# DEBUGGING FUNCTIONS #################################################################################################
def synthesis_debug(func):
    """A function decorator used to decorate modified
    functions in the original Django framework for
    debugging our imposed synthesis framework."""
    @functools.wraps(func)
    def get_class(method):
        """Get the class that defines the called function/method.
        It is unlikely that we encounter all cases defined below,
        but just for completeness.
        Ref: https://stackoverflow.com/a/25959545/9632613."""
        # If the method is a partial function
        if isinstance(method, functools.partial):
            return get_class(method.func)
        # If it is a method (bounded to a class)
        if inspect.ismethod(method) or \
            (inspect.isbuiltin(method) and
             getattr(method, '__self__', None) is not None and
             getattr(method.__self__, '__class__', None)):
            for cls in inspect.getmro(method.__self__.__class__):
                if method.__name__ in cls.__dict__:
                    return cls
            method = getattr(method, '__func__', method)  # fallback to __qualname__ parsing
        if inspect.isfunction(method):
            cls = getattr(inspect.getmodule(method),
                          method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0], None)
            if isinstance(cls, type):
                return cls
        return getattr(method, '__objclass__', None)  # handle special descriptor objects

    def wrapper(*args, **kwargs):
        # Get the name of the function
        func_name = func.__name__
        # Get the class that defines the called function (method)
        cls_name = get_class(func).__name__
        res = func(*args, **kwargs)
        res_type = type(res).__name__
        print("[SYNTHESIS DEBUG] {func} (in class: {cls}) -> ({type}) {res}".format(func=func_name,
                                                                                    cls=cls_name,
                                                                                    type=res_type,
                                                                                    res=res.to_trusted()))
        return res

    return wrapper
#######################################################################################################################


def to_untrusted(value, synthesized):
    """Convert a value to its corresponding untrusted
    type if exists. The flag will be set as synthesized.
    If no untrusted version exists, return itself."""
    if isinstance(value, UntrustedMixin):
        # If value is already an Untrusted type
        value.synthesized = synthesized
        return value
    # boolean value is always bool (bool is not extensible)
    # bool is a subclass of int, so we must check this first
    elif isinstance(value, bool):
        return value
    elif isinstance(value, int):
        return UntrustedInt(value, synthesized=synthesized)
    elif isinstance(value, float):
        return UntrustedFloat(value, synthesized=synthesized)
    elif isinstance(value, Decimal):
        return UntrustedDecimal(value, synthesized=synthesized)
    elif isinstance(value, str) or isinstance(value, UserString):
        return UntrustedStr(value, synthesized=synthesized)
    #####################################################
    # TODO: Add more casting here for new untrusted types
    #####################################################
    # Recursively convert values in list or other structured data
    # Note that we cannot use list/dict/set comprehension because
    # we do not want this function to create a new object (which
    # will not work well with recursion!
    elif isinstance(value, list):
        for i in range(len(value)):
            value[i] = to_untrusted(value[i], synthesized)
        return value
    elif isinstance(value, tuple):
        # Creating a new tuple is fine because tuple is immutable anyways
        return tuple(to_untrusted(v, synthesized) for v in value)
    elif isinstance(value, set):
        list_copy = []
        for v in value:
            list_copy.append(to_untrusted(v, synthesized))
        value.clear()
        value.update(list_copy)
        return value
    elif isinstance(value, dict):
        untrusted_dict = {to_untrusted(k, synthesized): to_untrusted(v, synthesized)
                          for k, v in value.items()}
        value.clear()
        value.update(untrusted_dict)
        return value
    # TODO: We may consider a generic Untrusted type,
    #  instead of returning a trusted value.
    else:
        return value


def is_synthesized(value):
    """A helper function that checks if a value
    contains a set (True) synthesized flag."""
    synthesized = False
    if isinstance(value, UntrustedMixin):
        return value.synthesized
    # recursively convert values in list or other structured data
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set):
        for v in value:
            if is_synthesized(v):
                synthesized = True
                break
    elif isinstance(value, dict):
        for k, v in value.items():
            if is_synthesized(k):
                synthesized = True
                break
            if is_synthesized(v):
                synthesized = True
                break
    return synthesized


def add_synthesis(func):
    """A function decorator that makes the original function
    (that are not synthesis-aware) return Untrusted values."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res is NotImplemented:
            return res
        # Set synthesized flag if any args/kwargs sets the flag
        synthesized = False
        for arg in args:
            if is_synthesized(arg):
                synthesized = True
                break
        for key, value in kwargs.items():
            if is_synthesized(value):
                synthesized = True
                break
        return to_untrusted(res, synthesized)
    return wrapper


def untrustify(func):
    """A function decorator that converts all trusted args and kwargs
    to their untrusted version. Values that cannot be untrustified
    will remain. This conversion always set the synthesized flag to False
    unless the value is already untrusted and it has a True synthesized flag."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, UntrustedMixin):
                args[i] = arg
            else:
                args[i] = to_untrusted(arg, synthesized=False)
        kwargs = dict(kwargs)
        for key, value in kwargs.items():
            if isinstance(value, UntrustedMixin):
                kwargs[key] = value
            else:
                kwargs[key] = to_untrusted(value, synthesized=False)
        return func(*args, **kwargs)
    return wrapper


def synthesis_check(func, warn):
    """A function decorator factory which builds various function decorator
    depends on warn parameter. Overall it checks if a synthesized value is
    returned from the original func. If warn is True, only warning is output;
    otherwise, ValueError is raised."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        synthesized = False
        res = func(*args, **kwargs)
        if is_synthesized(res):
            synthesized = res.synthesized
        if not synthesized:
            return res
        else:
            if warn:
                warnings.warn("Synthesized value output by {func} "
                              "might be used unintentionally".format(func=func.__name__),
                              category=RuntimeWarning,
                              stacklevel=2)
                return res
            else:
                raise RuntimeError("Synthesized value output by {func} "
                                   "should not be used at all".format(func=func.__name__))
    return wrapper


# Actual decorators manufactured by the synthesis_check decorator factory
synthesis_warning = functools.partial(synthesis_check, warn=True)
synthesis_error = functools.partial(synthesis_check, warn=False)


def add_synthesis_to_func(cls):
    """A class decorator that decorates all functions in cls
    so that they are synthesis-aware. If cls is a subclass of
    some base classes, then we want functions in base class to be
    synthesis-aware as well.

    Important note: Any cls (UntrustedX only) function to be decorated
    must start with either "synthesis_" or "_synthesis_" (for protected
    methods), while base class functions have no such restriction
    (since it is likely that developers have no control over the
    base class). Using this convention, developers can prevent
    base class functions from being decorated by overriding the
    function (and just calling base class function in the override).
    If, for example, the developer needs to override a dunder function,
    and the overridden function needs to be decorated, they should first
    implement a helper function '_synthesize__dunder__' and then
    call the helper function in the dunder function. As such,
    _synthesize__dunder__ will be decorated (and therefore the
    calling dunder function)."""
    # set of callable function names already been decorated/inspected
    handled_funcs = set()
    # First handle all functions in cls class
    # TODO: (non-urgent) __dict__ does not return __slots__
    #  so will not work if cls uses __slots__ instead of __dict__
    # NOTE: Do NOT use __dict__[key] to test callable(), use getattr() instead. Not because
    # of performance, but for more important reasons! For example, callable(__dict__["__new__"])
    # returns False because it is a class method (in fact, all static and class methods will
    # return False if use __dict__ instead of getattr() to obtain the function!
    # Reference:
    # https://stackoverflow.com/questions/14084897/getattr-versus-dict-lookup-which-is-faster
    for key in cls.__dict__:
        # Only callable functions are decorated
        value = getattr(cls, key)
        if not callable(value):
            continue
        # All callable functions are inspected in cls
        handled_funcs.add(key)
        # Decorate only 'synthesis_' or '_synthesis_' prefixed functions in cls
        if key.startswith("synthesis_") or key.startswith("_synthesis_"):
            setattr(cls, key, add_synthesis(value))

    # Handle base class functions if exists. Base classes are
    # unlikely to follow our synthesis naming convention.
    # However, some __dunder__ methods clearly should *not* be
    # decorated, even if they are callable, we will add them
    # in handled_funcs. Non-decorated methods will follow the
    # traditional MRO calling order!
    # Note that __dict__, __module__, __doc__ are not callable
    # so they will not be decorated in the first place.
    handled_funcs.update({'__repr__',
                          '__getattribute__',
                          '__new__',
                          '__format__',
                          '__class__',
                          })
    # __mro__ defines the list of *ordered* base classes
    # (the first being cls and the second being UntrustedMixin).
    # UntrustedMixin should *not* be decorated, add all of its callable functions in handled_funcs
    mixin_cls = cls.__mro__[1]      # IMPORTANT: UntrustedMixin MUST be the first parent class!
    for key in mixin_cls.__dict__:
        value = getattr(mixin_cls, key)
        if not callable(value):
            continue
        handled_funcs.add(key)
    # Handle the remaining base classes
    for base in cls.__mro__[2:]:
        for key in base.__dict__:
            value = getattr(base, key)
            # Only callable functions that are not handled by previous classes
            if not callable(value) or key in handled_funcs:
                continue
            # All callable functions are inspected in the current base class
            handled_funcs.add(key)
            # Delegate add_synthesis() to handle other cases
            # since there is not much convention we can specify.
            # Note that it is possible add_synthesis() can just
            # return the same function (value) with no changes.
            # Note that we are adding those attributes to cls!
            # Therefore, once decorated by add_synthesis(), cls
            # will always call the decorated function (since it
            # will be placed at the top of the MRO), not the one
            # in any of the superclasses!
            setattr(cls, key, add_synthesis(value))
    # NOTE: Function calling order (when called fom an UntrustedX object) --
    # 1. Original cls (UntrustedX) functions (decorated and non-decorated) and
    #    all decorated functions (including functions from all base classes).
    # 2. All functions defined in UntrustedMixin.
    # 3. All other non-decorated functions from classes other than UntrustedX
    #    and UntrustedMixin follow the original MRO.
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

    #  We comment out the following code, and use add_synthesis_to_func() to decorate
    #  __int__ instead. But here is the trade-off:
    #  1. If we use add_synthesis_to_func(), __int__ will still return UntrustedInt
    #     type and if the value is synthesized the returned value will also be synthesized;
    #     if we use the method below and if the original value is synthesized, we
    #     will receive a RuntimeError.
    #  2. However, if we use add_synthesis_to_func(), int() will cast both synthesized
    #     untrusted but non-synthesized value to int(), but if we use the method below,
    #     we will at least receive a RuntimeError.
    #  However, since developers should always use to_trusted() instead of explicit
    #  casting, we decide to use add_synthesis_to_func() like most other methods.
    # @add_synthesis
    # def __int__(self):
    #     """__int__ will not be decorated in add_synthesis_to_func() since we override
    #     it here. We re-decorate using @add_synthesis. We do this, instead of
    #     decorating __int__ directly in add_synthesis_to_func(), because
    #     1. Decorating __int__ does not change the fact that int() will ALWAYS
    #        returns an instance of EXACT int (reference:
    #        https://hg.python.org/cpython/rev/81f229262921). This is decided by
    #        CPython and cannot be changed at this level.
    #     2. Because of 1. the most we can do is to raise an error if int()
    #        conversion is performed on not just untrusted but synthesized value.
    #     3. We cannot do 2. if we decorate __int__ in add_synthesis_to_func().
    #     4. We use @add_synthesis to decorate __int__ here so that __int__() call
    #        still return UntrustedInt, but not int.
    #     This is safe conversion but conversion may still fail if the input to int()
    #     cannot be converted to an int."""
    #      if self.synthesized:
    #         raise RuntimeError("cannot convert a synthesized value to a trusted int value")
    #     else:
    #         return super().__int__()

    #  UPDATE: We decide to still override __int__ here to simply DISALLOW the use
    #          of int() altogether on UntrustedInt.
    def __int__(self):
        raise TypeError("cannot use int() to coerce to int. Use to_trusted() instead.")

    #  We comment out the following code for the same reason as in __int__ above.
    # @add_synthesis
    # def __float__(self):
    #     """__float__ is treated this way for the same reason as __int__ (see above).
    #     float() cannot return an instance of a strict subclass of float. The ability
    #     to return an instance of a strict subclass of float is deprecated (CPython).
    #     This is safe conversion but conversion may still fail if the input to float()
    #     cannot be converted to a float."""
    #     if self.synthesized:
    #         raise RuntimeError("cannot convert a synthesized value to a trusted float value")
    #     else:
    #         return super().__float__()

    #  UPDATE: We decide to still override __float__ here to simply DISALLOW the use
    #          of float() altogether on UntrustedInt.
    def __float__(self):
        raise TypeError("cannot use float() to coerce to float. Use to_trusted() instead.")

    #  NOTE: Unlike __int__ and __float__, __str__ and str() return TypeError: __str__ returned
    #  non-string (type UntrustedStr) if casting returns any other types than the built-in
    #  string type (e.g., UntrustedStr). This is good as we do NOT want to allow casting from
    #  UntrustedStr to str using str() or __str__; we want a more explicit casting call.
    #  Therefore, we can use add_synthesis_to_func() to directly decorate __str__ (basically
    #  this decoration will make sure that str() and __str__() will lead to a TypeError if used
    #  to cast UntrustedStr.
    # TODO: REMOVE THIS METHOD ONCE PRINT TO CONSOLE IS NO LONGER NEEDED
    def __str__(self):
        return super().__str__()

    def to_trusted(self, forced=False):
        """Convert a value to its corresponding trusted type. Conversion results in
        a RuntimeError if the untrusted value is synthesized, unless 'forced' is set
        to be True. If 'forced' is True, conversion always works. """
        if self.synthesized and not forced:
            raise RuntimeError("cannot convert a synthesized value to a trusted value")
        if not isinstance(self, UntrustedMixin):
            return self

        if isinstance(self, UntrustedInt):
            return super().__int__()
        elif isinstance(self, UntrustedFloat):
            return super().__float__()
        elif isinstance(self, UntrustedStr):
            return super().__str__()
        elif isinstance(self, UntrustedDecimal):
            return Decimal(self)
        # Last resort is that a generic object is wrapped in UntrustedObject
        # This means that the "else" branch likely will never be reached.
        elif isinstance(self, UntrustedObject):
            return self.object
        else:
            raise RuntimeError("cannot convert an unknown untrusted type")

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
        return input_integer % (2 ** 63 - 1)

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
        return type(self).custom_hash(self)


class UntrustedFloat(UntrustedMixin, float):
    """Subclass Python builtin float class and Untrusted Mixin."""
    def __new__(cls, x, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, x, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)


class UntrustedDecimal(UntrustedMixin, Decimal):
    """Subclass Python decimal module's Decimal class and Untrusted Mixin.
    Decimal is immutable, so we should override __new__ and not just __init__."""
    def __new__(cls, value="0", context=None, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, value, context, *args, **kwargs)
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


class UntrustedObject(UntrustedMixin):
    """To convert objects that cannot use other trusted types.
     Subclass only UntrustedMixin to add the untrusted feature."""
    def __init__(self, obj, *, synthesized=False):
        super().__init__(synthesized)
        self._obj = obj

    @property
    def object(self):
        return self._obj


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

    synthesized_float_8 = synthesized_int_1 / int_literal
    assert synthesized_float_8 == 2.4, "synthesized_float_8 should be 2.4, but it is {}.".format(synthesized_float_8)
    assert synthesized_float_8.synthesized is True, "synthesized_float_8 should be synthesized."
    assert type(synthesized_float_8) == UntrustedFloat, "synthesized_float_8 type is not UntrustedFloat"

    synthesized_float_9 = int_literal / synthesized_int_1
    assert synthesized_float_9 == 5 / 12, "synthesized_float_9 should be 5/12, " \
                                          "but it is {}.".format(synthesized_float_9)
    assert synthesized_float_9.synthesized is True, "synthesized_float_9 should be synthesized."
    assert type(synthesized_float_9) == UntrustedFloat, "synthesized_float_9 type is not UntrustedFloat"

    try:
        converted_int_1 = int(synthesized_int_6)
    except TypeError as e:
        print("60 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    try:
        converted_int_1 = synthesized_int_6.to_trusted()
    except RuntimeError as e:
        print("60 is synthesized, converting it to int using to_trusted() without force results in "
              "RuntimeError: {error}".format(error=e))
    assert type(synthesized_int_6.to_trusted(forced=True)) == int, "explicitly converted synthesized_int_6 is not int"

    try:
        converted_int_2 = int(untrusted_int_9)
    except TypeError as e:
        print("-5 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_int_9.to_trusted() == untrusted_int_9, "untrusted_int_9 should be -5, but it is not."
    assert type(untrusted_int_9.to_trusted()) == int, "explicitly converted untrusted_int_9 is not int"

    converted_int_3 = int(base_int)
    assert converted_int_3 == base_int, "converted_int_3 should be 10, but it is {}.".format(converted_int_3)
    assert type(converted_int_3) == int, "converted_int_3 type is not int"

    try:
        converted_float_1 = float(synthesized_int_6)
    except TypeError as e:
        print("60 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_float_2 = float(untrusted_int_9)
    except TypeError as e:
        print("-5 is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_int_9.to_trusted() == -5, "untrusted_int_9 should be -5, but it is not."
    assert type(float(untrusted_int_9.to_trusted())) == float, "explicitly converted untrusted_int_9 is not float"

    try:
        converted_str_1 = str(synthesized_int_6)
    except TypeError as e:
        print("60 is synthesized, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_str_2 = str(untrusted_int_9)
    except TypeError as e:
        print("-5 is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))


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

    untrusted_float_9 = UntrustedFloat(10)
    try:
        int_1 = int(untrusted_float_9)
    except TypeError as e:
        print("10.0 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(untrusted_float_9.to_trusted()) == 10, "untrusted_float_9 should be explicitly converted to 10, " \
                                                      "but it is not."
    assert type(int(untrusted_float_9.to_trusted())) == int, "explicitly converted untrusted_float_9 is not int"

    synthesized_float_3 = UntrustedFloat(10, synthesized=True)
    try:
        converted_int_2 = int(synthesized_float_3)
    except TypeError as e:
        print("10.0 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_float_1 = float(synthesized_float_2)
    except TypeError as e:
        print("68.75 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_float_2 = float(untrusted_float_7)
    except TypeError as e:
        print("4.5 is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_float_7.to_trusted() == 4.5, "untrusted_float_7 should be explicitly converted to 4.5, " \
                                                  "but it is not."
    assert type(untrusted_float_7.to_trusted()) == float, "explicitly converted untrusted_float_7 type is not float"

    try:
        converted_str_1 = str(untrusted_float_7)
    except TypeError as e:
        print("4.5 is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    assert str(untrusted_float_7.to_trusted()) == '4.5', "explicitly converted untrusted_float_7 should be '4.5', " \
                                                         "but it is not."
    assert type(str(untrusted_float_7.to_trusted())) == str, "explicitly converted untrusted_float_7 is not str"

    try:
        converted_str_2 = str(synthesized_float_2)
    except TypeError as e:
        print("68.75 is synthesized, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    try:
        converted_float_3 = synthesized_float_2.to_trusted()
    except RuntimeError as e:
        print("68.75 is synthesized, converting it to float using to_trusted() without force results in "
              "RuntimeError: {error}".format(error=e))
    assert type(synthesized_float_2.to_trusted(forced=True)) == float, "explicitly converted " \
                                                                       "synthesized_float_2 is not float"


def untrusted_decimal_test():
    base_decimal = Decimal('3.14')
    # Make sure UntrustedDecimal can take all forms acceptable by Decimal
    untrusted_decimal_1 = UntrustedDecimal('3.14')              # string input
    untrusted_decimal_2 = UntrustedDecimal((0, (3, 1, 4), -2))  # tuple (sign, digit_tuple, exponent)
    assert untrusted_decimal_2 == Decimal((0, (3, 1, 4), -2)), "untrusted_decimal_2 should be 3.14, " \
                                                               "but it is {}".format(untrusted_decimal_2)
    assert type(untrusted_decimal_2) is UntrustedDecimal, "untrusted_decimal_2 type is not UntrustedDecimal"
    untrusted_decimal_3 = UntrustedDecimal(Decimal(314))        # another decimal instance
    assert untrusted_decimal_3 == Decimal(Decimal(314)), "untrusted_decimal_3 should be 314, " \
                                                         "but it is {}".format(untrusted_decimal_3)
    assert type(untrusted_decimal_3) is UntrustedDecimal, "untrusted_decimal_3 type is not UntrustedDecimal"
    untrusted_decimal_4 = UntrustedDecimal('  3.14 \n')         # leading and trailing whitespace is okay
    assert untrusted_decimal_4 == Decimal('  3.14 \n'), "untrusted_decimal_4 should be 3.14, " \
                                                        "but it is {}".format(untrusted_decimal_4)
    assert type(untrusted_decimal_4) is UntrustedDecimal, "untrusted_decimal_4 type is not UntrustedDecimal"
    untrusted_decimal_5 = UntrustedDecimal(314)                 # int
    assert untrusted_decimal_5 == Decimal(314), "untrusted_decimal_5 should be 314, " \
                                                "but it is {}".format(untrusted_decimal_5)
    assert type(untrusted_decimal_5) is UntrustedDecimal, "untrusted_decimal_5 type is not UntrustedDecimal"
    synthesized_decimal_1 = UntrustedDecimal('3.14', synthesized=True)

    untrusted_decimal_6 = base_decimal + untrusted_decimal_1
    assert untrusted_decimal_6 == base_decimal + base_decimal, "untrusted_decimal_6 should be 6.28, " \
                                                               "but it is {}.".format(untrusted_decimal_6)
    assert untrusted_decimal_6.synthesized is False, "untrusted_decimal_6 should not be synthesized."
    assert type(untrusted_decimal_6) == type(untrusted_decimal_1), "untrusted_decimal_6 type is not UntrustedDecimal"

    untrusted_decimal_7 = base_decimal * untrusted_decimal_1
    assert untrusted_decimal_7 == base_decimal * base_decimal, "untrusted_decimal_7 should be 9.8596, " \
                                                               "but it is {}.".format(untrusted_decimal_6)
    assert untrusted_decimal_7.synthesized is False, "untrusted_decimal_7 should not be synthesized."
    assert type(untrusted_decimal_7) == type(untrusted_decimal_1), "untrusted_decimal_7 type is not UntrustedDecimal"

    synthesized_decimal_2 = base_decimal * synthesized_decimal_1
    assert synthesized_decimal_2 == base_decimal * base_decimal, "synthesized_decimal_2 should be 9.8596, " \
                                                                 "but it is {}.".format(untrusted_decimal_6)
    assert synthesized_decimal_2.synthesized is True, "synthesized_decimal_2 should be synthesized."
    assert type(synthesized_decimal_2) == type(untrusted_decimal_1), \
        "synthesized_decimal_2 type is not UntrustedDecimal"

    untrusted_decimal_8 = UntrustedDecimal(10)
    try:
        converted_int_1 = int(untrusted_decimal_8)
    except TypeError as e:
        print("10 is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_decimal_8.to_trusted() == 10, "explicitly converted untrusted_decimal_8 should be 10, " \
                                                   "but it is not."

    synthesized_decimal_3 = UntrustedDecimal(10, synthesized=True)
    try:
        converted_int_2 = int(synthesized_decimal_3)
    except TypeError as e:
        print("10 is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_float_1 = float(synthesized_decimal_1)
    except TypeError as e:
        print("3.14 is synthesized, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_float_2 = float(untrusted_decimal_7)
    except TypeError as e:
        print("9.8596 is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_decimal_7.to_trusted() == untrusted_decimal_7, "explicitly converted untrusted_decimal_7 " \
                                                                    "should be equal to untrusted_decimal_7 " \
                                                                    "but it is not."
    assert type(float(untrusted_decimal_7.to_trusted())) == float, "explicitly converted untrusted_decimal_7 " \
                                                                   "is not float"

    try:
        converted_str_1 = str(untrusted_decimal_7)
    except TypeError as e:
        print("9.8596 is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))

    try:
        converted_str_2 = str(synthesized_decimal_1)
    except TypeError as e:
        print("3.14 is synthesized, converting it to str using str() results in "
              "error: {error}".format(error=e))


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

    untrusted_str_4 = UntrustedStr("10")
    try:
        converted_int_1 = int(untrusted_str_4)
    except TypeError as e:
        print("'10' is untrusted, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))
    assert int(untrusted_str_4.to_trusted()) == 10, "explicitly converted untrusted_str_4 should be 10, " \
                                                    "but it is not."
    assert type(int(untrusted_str_4.to_trusted())) == int, "explicitly converted untrusted_str_4 is not int"

    synthesized_str_5 = UntrustedStr("10", synthesized=True)
    try:
        converted_int_2 = int(synthesized_str_5)
    except TypeError as e:
        print("'10' is synthesized, converting it to int using int() results in "
              "TypeError: {error}".format(error=e))

    untrusted_str_5 = UntrustedStr("10.5")
    try:
        converted_float_1 = float(untrusted_str_5)
    except TypeError as e:
        print("'10.5' is untrusted, converting it to float using float() results in "
              "TypeError: {error}".format(error=e))
    assert float(untrusted_str_5.to_trusted()) == 10.5, "explicitly converted untrusted_str_5 should be 10.5, " \
                                                        "but it is not."
    assert type(float(untrusted_str_5.to_trusted())) == float, "explicitly converted untrusted_str_5 is not float"

    synthesized_str_6 = UntrustedStr("10.5", synthesized=True)
    try:
        converted_float_2 = synthesized_str_6.to_trusted()
    except RuntimeError as e:
        print("'10.5' is synthesized, converting it to float using to_trusted() without force results in "
              "error: {error}".format(error=e))

    try:
        converted_str_1 = str(untrusted_str)
    except TypeError as e:
        print("'Untrusted World!' is untrusted, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))
    assert untrusted_str.to_trusted() == 'Untrusted World!', "explicitly converted untrusted_str should be " \
                                                             "'Untrusted World!, but it is not."
    assert type(untrusted_str.to_trusted()) == str, "explicitly converted untrusted_str type is not str"

    try:
        converted_str_2 = str(synthesized_str)
    except TypeError as e:
        print("'Fake World!' is synthesized, converting it to str using str() results in "
              "TypeError: {error}".format(error=e))


if __name__ == "__main__":
    untrusted_int_test()
    untrusted_float_test()
    untrusted_decimal_test()
    untrusted_str_test()
