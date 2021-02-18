"""
Tools to make built-in types and any existing Python class untrusted
and trust-aware. An untrusted class must subclass UntrustedMixin while
a trust-aware class must subclass TrustAwareMixin. Both of them must
also subclass the built-in types or any existing Python class. Once
a trust-aware class is created, it can shadow the original class so
that all data types are either trust-aware or untrusted.
"""

import functools
import warnings

from django.splice.archive import replace


# Special methods that should not be decorated.
do_not_decorate = {'__init__',
                   '__del__',
                   '__getattr__',
                   '__getattribute__',
                   '__setattr__',
                   '__delattr__',
                   '__dir__',
                   '__get__',
                   '__set__',
                   '__delete__',
                   '__set_name__',
                   '__slots__',
                   '__prepare__',
                   '__class__',
                   '__iter__',
                   '__reversed__',
                   '__enter__',
                   '__exit__',
                   '__subclasshook__',
                   '__subclasscheck__',
                   '__instancecheck__',
                   }


def is_untrusted(value):
    """Checks if a value is/contains untrusted data."""
    untrusted = False
    if isinstance(value, UntrustedMixin):
        return True
    # Recursively check values in a list or other data structures
    # FIXME: for data structures with key/value pairs, if __iter__ returns
    #  keys only (in the for loop), then only keys are checked. BaseStruct
    #  is not checked! Perhaps a checker class is a better choice.
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set) or isinstance(value, dict):
        for v in value:
            if is_untrusted(v):
                untrusted = True
                break
    return untrusted


def is_synthesized(value):
    """Check if a value contains a synthesized flag set to be True."""
    synthesized = False
    if isinstance(value, UntrustedMixin):
        return value.synthesized
    # Recursively check values in a list or other data structures
    # FIXME: for data structures with key/value pairs, if __iter__ returns
    #  keys only (in the for loop), then only keys are checked. BaseStruct
    #  is not checked! Perhaps a checker class is a better choice.
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set) or isinstance(value, dict):
        for v in value:
            if is_synthesized(v):
                synthesized = True
                break
    return synthesized


def contains_untrusted_arguments(*args, **kwargs):
    """Check if arguments passed into a function/method contains untrusted and synthesized value."""
    untrusted = False
    synthesized = False
    for arg in args:
        if is_untrusted(arg):
            untrusted = True
        if is_synthesized(arg):
            synthesized = True
            return untrusted, synthesized
    for _, v in kwargs.items():
        if is_untrusted(v):
            untrusted = True
        if is_synthesized(v):
            synthesized = True
            return untrusted, synthesized
    return untrusted, synthesized


def to_trusted(value, forced=False):
    """
    Explicitly coerce a value to its trusted type, if the value is
    untrusted, by calling value's to_trusted() method. Conversion
    results in a RuntimeError if the untrusted value is synthesized,
    unless 'forced' is set to be True. If 'forced' is True, conversion
    always works. If value is not of an untrusted type, the same value
    is returned if it is trust-aware. Otherwise, convert to a
    trust-aware object if possible
    """
    if isinstance(value, UntrustedMixin):
        return value.to_trusted(forced)
    elif isinstance(value, TrustAwareMixin):
        return value
    else:
        return TrustAwareMixin.to_trust_aware(value)


def to_untrusted(value, synthesized):
    """Explicitly coerce a value to its untrusted type"""
    if isinstance(value, UntrustedMixin):
        return value
    else:
        return UntrustedMixin.to_untrusted(value, synthesized)


def untrusted_return(func):
    """A function decorator that makes the original function to return untrusted (but not synthesized) value."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        # Some quick return (no need to wrap those)
        if res is NotImplemented or res is None:
            return res
        return to_untrusted(res, synthesized=False)

    return wrapper


class UntrustedMixin(object):
    """
    A Mixin class for creating an untrusted class from an existing class.

    Important note: for __init_subclass__'s to_untrusted_cls() to work,
    UntrustedMixin must used as the *first* parent class in a subclass.
    """

    register_cls = {}

    def __init__(self, synthesized=False, *args, **kwargs):
        """A synthesized flag to identify if a value is synthesized."""

        # Forwards all unused arguments to other base classes down the MRO.
        self._synthesized = synthesized
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        """
        Whenever a class inherits from this, this special method is called on the cls,
        so that we can change the behavior of subclasses. This is closely related to
        class decorators, but where class decorators only affect the specific class
        they’re applied to, __init_subclass__ solely applies to future subclasses of
        the class defining the method. Here we use both __init_subclass__ and class
        decorator, so that a subclass of UntrustedMixin and its subclasses can be decorated.
        """

        UntrustedMixin.to_untrusted_cls(cls)
        UntrustedMixin.register(cls)

    @staticmethod
    def to_untrusted(value, synthesized):
        """
        Convert a value to its corresponding untrusted
        type if the type exists. The flag will be set
        as "synthesized". If there exists no corresponding
        untrusted version, we return the value itself.
        If value is already an untrusted value, this
        function can be used to modify synthesized flag.
        """
        # If value is already an Untrusted type
        if isinstance(value, UntrustedMixin):
            value.synthesized = synthesized
            return value
        # bool is a subclass of int, so we must check it first
        # bool cannot be usefully converted to an untrusted type
        elif isinstance(value, bool):
            return value
        # Conversion happens here. We only know how to convert
        # classes that are registered (i.e., classes that subclass
        # UntrustedMixin, which automatically registers the class)
        # If "value" is of a trust-aware type, the registered class
        # is the native class in its MRO.
        registered_cls = value.__class__.__name__
        if isinstance(value, TrustAwareMixin):
            registered_cls = value.__class__.__bases__[1].__name__
        if registered_cls in UntrustedMixin.register_cls:
            return UntrustedMixin.register_cls[registered_cls].untrustify(value, synthesized)
        #####################################################
        #  Recursively convert values in list or other structured data
        #  Note that we do not just use list/dict/set comprehension as
        #  we do not want this function to create a new list/dict/set
        #  object since lists/dicts/sets are mutable and may be passed
        #  around in recursive functions to be mutated.
        elif isinstance(value, list):
            for i in range(len(value)):
                value[i] = UntrustedMixin.to_untrusted(value[i], synthesized)
            return value
        elif isinstance(value, tuple):
            # Creating a new tuple is fine because tuple is immutable
            return tuple(UntrustedMixin.to_untrusted(v, synthesized) for v in value)
        # Cannot modify a set during iteration, so we do it this way:
        elif isinstance(value, set):
            list_copy = [UntrustedMixin.to_untrusted(v, synthesized) for v in value]
            value.clear()
            value.update(list_copy)
            return value
        # Cannot modify a dict during iteration, so we do it this way:
        elif isinstance(value, dict):
            untrusted_dict = {UntrustedMixin.to_untrusted(k, synthesized): UntrustedMixin.to_untrusted(v, synthesized)
                              for k, v in value.items()}
            value.clear()
            value.update(untrusted_dict)
            return value
        # FIXME: We may consider a generic Untrusted type, or raising an error.
        else:
            warnings.warn("{value} (of type {type}) has no untrusted type defined".format(value=value,
                                                                                          type=type(value)),
                          category=RuntimeWarning,
                          stacklevel=2)
            return value

    @staticmethod
    def to_untrusted_cls(cls):
        """
        A class decorator that decorates all methods in a cls so that
        they return untrusted values, if needed. If cls is a subclass of
        some base classes, then we want functions in base classes to be
        able to return untrusted values as well.

        Important note: Any cls (i.e., UntrustedX) method to be decorated
        must start with either "untrusted_" or "_untrusted_" (for protected
        methods), while base class methods have no such restriction (since
        it is likely that developers have no control over the base classes).
        Using this convention, developers can prevent base class methods
        from being decorated by overriding the function (and then just call
        the base class method in the override method). If, for example,
        the developer needs to override a special "dunder" method, and
        the overridden method needs to be decorated, they should first
        implement a helper function '_untrusted__XXX__' and then call the
        helper function in the special method. As such, _untrusted__XXX__
        will be decorated (and therefore the calling special method).
        """

        def to_untrusted_method(func):
            """
            A function decorator that makes the original function (that
            may not be trust-aware) return untrusted values if possible.
            """

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Calling native methods (including built-in methods) - IMPORTANT NOTE:
                # "res" usually return objects of native (including built-in) types, but it is
                # possible that "res" returns objects of untrusted types already. This is OK
                # because UntrustedMixin.to_untrusted() will return the same object if it is
                # already of an untrusted type.
                #
                # NOTE -- In old implementation of UntrustedStr, "res" returns directly
                # UntrustedStr because UserString (subclassed by UntrustedStr) returns
                # self.__class__. But this is no longer the case for the new implementation
                # since it now inherits from the built-in str.

                # TODO: does this *always* make sense?
                _, synthesized = contains_untrusted_arguments(*args, **kwargs)
                res = func(*args, **kwargs)
                # FIXME: perhaps there are more cases where conversion
                #  should occur but the "func" does not return None!
                if res is None:
                    # See if "self" is an untrusted object and if it needs
                    # to be converted a synthesized object by setting its
                    # "synthesized" attribute to True.
                    if isinstance(args[0], UntrustedMixin):
                        if synthesized:
                            args[0].synthesized = True
                    return res
                # Some other quick return (no need to wrap those)
                if res is NotImplemented:
                    return res
                return UntrustedMixin.to_untrusted(res, synthesized)

            return wrapper

        # set of callable method names already been decorated/inspected
        handled_methods = set()
        # First handle all methods in cls class
        # TODO: __dict__ does not return __slots__, so will
        #  not work if cls uses __slots__ instead of __dict__
        # NOTE: Do NOT use __dict__[key] to test callable(), use getattr() instead. Not because
        # of performance, but for more important reasons! For example, callable(__dict__["__new__"])
        # returns False because it is a class method (in fact, all static and class methods will
        # return False if use __dict__ instead of getattr() to obtain the method!
        # Reference:
        # https://stackoverflow.com/questions/14084897/getattr-versus-dict-lookup-which-is-faster
        for key in cls.__dict__:
            # Only callable methods are decorated
            value = getattr(cls, key)
            if not callable(value):
                continue
            # All callable methods are inspected in cls
            handled_methods.add(key)
            # Decorate only 'untrusted_' or '_untrusted_' prefixed methods in cls.
            # See example usage in __hash__() in UntrustedInt and UntrustedStr.
            if key.startswith("untrusted_") or key.startswith("_untrusted_"):
                setattr(cls, key, to_untrusted_method(value))
        # Handle base class methods if exists. Base classes are
        # unlikely to follow our synthesis naming convention.
        # However, some special methods clearly should *not* be
        # decorated, even if they are callable. We will add them
        # in handled_methods. Non-decorated methods will follow
        # the original MRO! Note that __dict__, __module__,
        # and __doc__ are not callable, so they will not be
        # decorated in the first place.
        handled_methods.update(do_not_decorate)
        # __mro__ defines the list of *ordered* base classes
        # (the first being cls and the second being UntrustedMixin).
        # UntrustedMixin should *not* be decorated, so add them all in handled_methods
        mixin_cls = cls.__mro__[1]  # IMPORTANT: UntrustedMixin MUST be the second class in MRO!
        for key in mixin_cls.__dict__:
            value = getattr(mixin_cls, key)
            if not callable(value):
                continue
            handled_methods.add(key)
        # Handle the remaining base classes
        for base in cls.__mro__[2:]:
            # We should skip TrustAwareX and TrustAwareMixin. They
            # are simply thin layers wrapping actual base classes.
            if "TrustAware" in base.__name__:
                continue
            for key in base.__dict__:
                value = getattr(base, key)
                # Only callable methods that are not handled already
                if not callable(value) or key in handled_methods:
                    continue
                # All callable methods are inspected in the current base class
                handled_methods.add(key)
                # Delegate to_untrusted_method() to handle other cases
                # since there is not much convention we can specify.
                # Note that it is possible to_untrusted_method() can just
                # return the same method output without any changes.
                # Note also that we are adding those attributes to cls!
                # Therefore, once decorated by to_untrusted_method(),
                # cls will always call the decorated methods (since they
                # will be placed at the front of the MRO), not the ones
                # in any of the base classes!
                setattr(cls, key, to_untrusted_method(value))
        # NOTE: The new MRO after decoration (when called from UntrustedX) --
        # 1. Original cls (UntrustedX) methods (decorated and non-decorated) and
        #    all decorated methods.
        # 2. All methods defined in UntrustedMixin.
        # 3. All other non-decorated methods from classes other than UntrustedX
        #    and UntrustedMixin following the original MRO.
        return cls

    def to_trusted(self, forced=False):
        """
        Convert a value to its corresponding trusted type. Conversion results in
        a RuntimeError if the untrusted value is synthesized, unless 'forced' is set
        to be True. If 'forced' is True, conversion always works.
        """

        if self.synthesized and not forced:
            raise RuntimeError("cannot convert a synthesized value to a trusted value")
        if not isinstance(self, UntrustedMixin):
            return self
        else:
            native = UntrustedMixin.register_cls[type(self).__name__]
            # Check if there is a trusted type registered for conversion
            if native in TrustAwareMixin.register_cls:
                return TrustAwareMixin.register_cls[native].trustify(self)
            else:
                raise TypeError("{} does not have a corresponding trusted type".format(type(self).__name__))

    @staticmethod
    def register(cls):
        """Register the untrusted class with its native counterpart so conversion can be automated."""

        native = cls.__mro__[2]  # IMPORTANT: the native (including built-in) class MUST be the third class in MRO!
        UntrustedMixin.register_cls[native.__name__] = cls
        UntrustedMixin.register_cls[cls.__name__] = native.__name__

    #  We wanted to use to_untrusted_cls() to decorate __int__, but here is the trade-off:
    #  1. If we were to use to_untrusted_cls(), __int__ will return UntrustedInt.
    #     If the value is synthesized, the returned value will also be synthesized.
    #     If we were to use the method below instead, and if the original value is
    #     synthesized, we will receive a RuntimeError.
    #  2. However, if we were to use to_untrusted_cls(), int() would cast both synthesized
    #     and non-synthesized value to int. This is because __int__ does not change
    #     the fact that int() will ALWAYS return an instance of EXACT int (reference:
    #     https://hg.python.org/cpython/rev/81f229262921), as enforced by Python.
    #     But if we were to use the method below, we would at least receive a RuntimeError
    #     for synthesized values.
    #  However, since developers should always use to_trusted() instead of casting directly
    #  through int(), we decide to simply override __int__ here to just DISALLOW the use of
    #  int() altogether on untrusted values.
    # @add_synthesis
    # def __int__(self):
    #      if self.synthesized:
    #         raise RuntimeError("cannot convert a synthesized value to a trusted int value")
    #     else:
    #         return super().__int__()
    def __int__(self):
        raise TypeError("cannot use int() to coerce an untrusted value to int. Use to_trusted() instead.")

    #  We decide to override __float__ here to simply DISALLOW the use of float() altogether
    #  on untrusted values for the same reason as __int__.
    # @add_synthesis
    # def __float__(self):
    #     if self.synthesized:
    #         raise RuntimeError("cannot convert a synthesized value to a trusted float value")
    #     else:
    #         return super().__float__()
    def __float__(self):
        raise TypeError("cannot use float() to coerce an untrusted value to float. Use to_trusted() instead.")

    # We wanted to override __bool__() but __bool__() must return a bool object, nothing else.

    #  NOTE: In old implementation, str() return TypeError: __str__ returned non-string (type
    #  UntrustedStr) because UntrustedStr is *not* a subclass of str. Because of this, we do
    #  NOT need to override __str__ or other similar methods. Now that we subclass from the
    #  built-in str type, we will have to override (like in __int__) to make sure casting from
    #  an untrusted value to str raises the same TypeError, because we want programmers to use
    #  the explicit type coercion call. The same applies to __repr__ (repr()), and __format__
    #  (format()).
    def __str__(self):
        raise TypeError("cannot use str() to coerce an untrusted value to str. Use to_trusted() instead.")

    def __repr__(self):
        raise TypeError("cannot use repr() to coerce an untrusted value to str. Use to_trusted() instead.")

    def __format__(self, format_spec):
        raise TypeError("cannot use repr() to coerce an untrusted value to str. Use to_trusted() instead.")

    def __iter__(self):
        """Define __iter__ so the iterator returns an untrusted value."""
        for x in super().__iter__():
            yield to_untrusted(x, self.synthesized)

    @property
    def synthesized(self):
        return self._synthesized

    @synthesized.setter
    def synthesized(self, synthesized):
        self._synthesized = synthesized

    @classmethod
    def untrustify(cls, value, flag):
        """Convert a value to its untrusted type and set the synthesized flag to flag."""
        raise NotImplementedError("Subclassed inherited from UntrustedMixin must implement untrustify()")


class TrustAwareMixin(object):
    """
    A Mixin class for adding trust-awareness to an existing Python class.

    Important note: for __init_subclass__'s to_trust_aware_cls() to work
    TrustAwareMixin must used as the *first* parent class in a subclass.
    """

    register_cls = {}

    def __init_subclass__(cls, **kwargs):
        TrustAwareMixin.register(cls)
        TrustAwareMixin.to_trust_aware_cls(cls)

    @classmethod
    def to_trust_aware(cls, value):
        """
        Convert a value to its corresponding trust-aware
        type if the type exists. If there exists no
        corresponding trusted-aware version, we return
        the value itself (but untrustiness may no longer
        propagate). If value is already trust-aware, do nothing.
        """
        # If value is already trust-aware
        if isinstance(value, TrustAwareMixin):
            return value
        # bool is a subclass of int, so we must check it first
        # bool cannot be usefully converted to be trust-aware
        elif isinstance(value, bool):
            return value
        # Conversion happens here. We only know how to convert
        # classes that are registered (i.e., classes that subclass
        # TrustAwareMixin, which automatically registers the class)
        elif value.__class__.__name__ in TrustAwareMixin.register_cls:
            return TrustAwareMixin.register_cls[value.__class__.__name__].trustify(value)
        #####################################################
        #  Recursively convert values in list or other structured data
        elif isinstance(value, list):
            for i in range(len(value)):
                value[i] = TrustAwareMixin.to_trust_aware(value[i])
            return value
        elif isinstance(value, tuple):
            # Creating a new tuple is fine because tuple is immutable
            return tuple(TrustAwareMixin.to_trust_aware(v) for v in value)
        # Cannot modify a set during iteration, so we do it this way:
        elif isinstance(value, set):
            list_copy = [TrustAwareMixin.to_trust_aware(v) for v in value]
            value.clear()
            value.update(list_copy)
            return value
        # Cannot modify a dict during iteration, so we do it this way:
        elif isinstance(value, dict):
            trusted_dict = {TrustAwareMixin.to_trust_aware(k): TrustAwareMixin.to_trust_aware(v)
                            for k, v in value.items()}
            value.clear()
            value.update(trusted_dict)
            return value
        else:
            return value

    @staticmethod
    def to_trust_aware_cls(cls):
        """This function is similar in design to to_untrusted_cls() in UntrustedMixin."""

        def to_trust_aware_method(func):
            """A function decorator to make a regular Python class trust-aware."""

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Calling native methods (including built-in methods) - IMPORTANT NOTE:
                # "res" usually return objects of native (including built-in) types, but it is
                # possible that "res" returns objects of trust-aware types already. This is
                # OK if the object is not going to be converted to untrusted later, because
                # TrustAwareMixin.to_trust_aware() will return the same object if it is already
                # of a trust-aware type. If the object will be converted to an untrusted
                # type later, we will let UntrustedMixin to handle this. We must also consider
                # methods on a *mutable* object that modify the object (self) in-place. For
                # example, appending an untrusted value to a trust-aware bytearray modifies
                # the mutable trust-aware bytearray object, but we should return an untrusted
                # bytearray object, not the same trust-aware one.
                #
                # NOTE -- In old implementation of TrustAwareStr, "res" returns directly
                # TrustAwareStr because UserString (subclassed by TrustAwareStr) returns
                # self.__class__. But this is no longer the case for the new implementation
                # since it now inherits from the built-in str.
                #
                # Return an untrusted type if *any* args/kwargs is of an untrusted
                # type. Also check if any args/kwargs has its synthesized flag set.
                # TODO: does this *always* make sense?
                untrusted, synthesized = contains_untrusted_arguments(*args, **kwargs)
                res = func(*args, **kwargs)
                # FIXME: perhaps there are more cases where conversion
                #  should occur but the "func" does not return None!
                if res is None:
                    # See if "self" is a trust-aware object and if it needs
                    # to be converted to the corresponding untrusted object.
                    if isinstance(args[0], TrustAwareMixin):
                        if untrusted:
                            replace(args[0], UntrustedMixin.to_untrusted(args[0], synthesized))
                    return res
                # Some other quick return (no need to wrap those)
                if res is NotImplemented:
                    return res
                # Convert to untrusted type instead of trusted type if input contains untrusted values
                if untrusted:
                    return UntrustedMixin.to_untrusted(res, synthesized)
                else:
                    # Convert to trusted type here
                    return TrustAwareMixin.to_trust_aware(res)

            return wrapper

        # set of callable method names already been decorated/inspected
        handled_methods = set()
        # TODO: __dict__ does not return __slots__, so will
        #  not work if cls uses __slots__ instead of __dict__
        # Skip all methods in cls class. cls really shouldn't define anything anyways.
        for key in cls.__dict__:
            # Only callable methods are decorated
            value = getattr(cls, key)
            if not callable(value):
                continue
            # All callable methods are inspected in cls
            handled_methods.add(key)
        # Handle base class methods if exists.
        handled_methods.update(do_not_decorate)
        # __mro__ defines the list of *ordered* base classes
        # (the first being cls and the second being TrustAwareMixin).
        # TrustAwareMixin should *not* be decorated, so add them all in handled_methods
        mixin_cls = cls.__mro__[1]  # IMPORTANT: TrustAwareMixin MUST be the second class in MRO!
        for key in mixin_cls.__dict__:
            value = getattr(mixin_cls, key)
            if not callable(value):
                continue
            handled_methods.add(key)
        # Handle the remaining base classes
        for base in cls.__mro__[2:]:
            for key in base.__dict__:
                value = getattr(base, key)
                # Only callable methods that are not handled already
                if not callable(value) or key in handled_methods:
                    continue
                # All callable methods are inspected in the current base class
                handled_methods.add(key)
                setattr(cls, key, to_trust_aware_method(value))
        return cls

    @staticmethod
    def register(cls):
        """Register the trust-aware class with the original Python class."""

        native = cls.__mro__[2]  # IMPORTANT: the native (including built-in) class MUST be the third class in MRO!
        TrustAwareMixin.register_cls[native.__name__] = cls

    @classmethod
    def trustify(cls, value):
        """Convert a Python value (self) to its trusted type. "value" can be of an untrusted type. """
        raise NotImplementedError("Subclassed inherited from TrustAwareMixin must implement trustify()")

    def __iter__(self):
        """Define __iter__ so the iterator returns a trust aware value."""
        for x in super().__iter__():
            yield to_trusted(x)
