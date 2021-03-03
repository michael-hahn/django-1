import functools
import warnings
import copy
from bitarray import bitarray
from django.splice.utils import is_class_method, is_static_method
from django.splice.identity import TaintSource


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
                   # != is used in the decoration function . We cannot decorate methods used
                   # in decoration, because doing so would create an infinite recursion!
                   # Decorating methods that return a bool value does nothing anyways.
                   '__ne__',
                   # Pickling Class Instances. deepcopy() might call them for pickling,
                   # and deepcopy is used in decoration. They shouldn't be decorated anyways.
                   # (ref: https://docs.python.org/3/library/pickle.html#pickling-class-instances)
                   '__getnewargs_ex__',
                   '__getnewargs__',
                   '__getstate__',
                   '__setstate__',
                   '__reduce__',
                   '__reduce_ex__',
                   '__deepcopy__',
                   }


def is_untrusted(value):
    """Checks if a value is/contains untrusted data."""
    if isinstance(value, SpliceMixin):
        return not value.trusted
    # Recursively check values in a list or other data structures
    # FIXME: for data structures with key/value pairs, if __iter__ returns
    #  keys only (in the for loop), then only keys are checked.
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set) or isinstance(value, dict):
        for v in value:
            if is_untrusted(v):
                return True
    return False


def is_synthesized(value):
    """Check if a value is/contains synthesized data."""
    if isinstance(value, SpliceMixin):
        return value.synthesized
    # Recursively check values in a list or other data structures
    # FIXME: for data structures with key/value pairs, if __iter__ returns
    #  keys only (in the for loop), then only keys are checked.
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set) or isinstance(value, dict):
        for v in value:
            if is_synthesized(v):
                return True
    return False


def contains_untrusted_arguments(*args, **kwargs):
    """Check if arguments passed into a function/method contains untrusted and synthesized value."""
    untrusted = False
    for arg in args:
        if is_synthesized(arg):
            return True, True
        elif is_untrusted(arg):
            untrusted = True
    for _, v in kwargs.items():
        if is_synthesized(v):
            return True, True
        elif is_untrusted(v):
            untrusted = True
    return untrusted, False


def is_tainted_by(value, taints):
    """Store the taint(s) of a value to "taints" argument. Note that taints can be None. """
    if isinstance(value, SpliceMixin):
        if value.taints is not None:
            taints |= value.taints
        return
    # Recursively check values in a list or other data structures
    # FIXME: for data structures with key/value pairs, if __iter__ returns
    #  keys only (in the for loop), then only keys are checked.
    elif isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set) or isinstance(value, dict):
        for v in value:
            is_tainted_by(v, taints)
    return


def union_argument_taints(*args, **kwargs):
    """
    Return a union of all taints associated with args and kwargs. Note that the return object
    is *never* None. If no taints, this function will return a bitarray of all 0s.
    """
    # Initialize a bitarray of zeros
    taints = bitarray(TaintSource.MAX_USERS, endian='big')
    taints.setall(False)
    for arg in args:
        is_tainted_by(arg, taints)
    for _, v in kwargs.items():
        is_tainted_by(v, taints)
    return taints


def to_trusted(value, forced=False):
    """
    Explicitly coerce an object to be trusted, if the object is splice-aware
    by calling object's to_trusted() method. Conversion results in a
    RuntimeError if the untrusted object is synthesized, unless 'forced' is
    set to be True. If 'forced' is True, conversion always works. If object
    is not splice-aware, the object is convert to a splice-aware object and
    the object has no taints.
    """
    if isinstance(value, SpliceMixin):
        return value.to_trusted(forced)
    else:
        return SpliceMixin.to_splice(value, True, False, None)


def untrusted(func):
    """
    A function decorator that makes the original function (that
    may not be splice-aware) return untrusted object if defined.
    Note that the object is only set to be untrusted but not
    synthesized; therefore, do not use this decorator if the
    return object might be synthesized!

    It also sets the object's taint to the taint of the current
    user. This decorator is designed primarily for forms.fields
    to_python() methods!
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        # Some quick return
        if res is NotImplemented or res is None:
            return res
        res = to_untrusted(res)
        return add_taints(res, TaintSource.current_user_taint)

    return wrapper


def to_untrusted(value):
    """
    Explicitly coerce an object to be untrusted, if the object is Splice-aware
    by setting its trusted flag to False. If object is not Splice-aware, the
    object is convert to an untrusted splice-aware object (but not synthesized).
    The newly-converted Splice-aware object also has no taints.
    """
    if isinstance(value, SpliceMixin):
        value.trusted = False
        return value
    else:
        return SpliceMixin.to_splice(value, False, False, None)


def to_synthesized(value):
    """
    Explicitly coerce an object to be synthesized, if the object is Splice-aware
    by setting its synthesized flag to True. If object is not Splice-aware, the
    object is convert to an untrusted and synthesized splice-aware object, but the
    newly-converted Splice-aware object has no taints.
    """
    if isinstance(value, SpliceMixin):
        value.synthesized = True
        return value
    else:
        return SpliceMixin.to_splice(value, False, True, None)


def add_taints(value, taints):
    """
    Explicitly add taints to an object, if the object is Splice-aware
    by setting its taints attribute. If object is not Splice-aware, the
    object is convert to a tainted (but trusted) splice-aware object.
    """
    if isinstance(value, SpliceMixin):
        value.taints = taints
        return value
    else:
        return SpliceMixin.to_splice(value, True, False, taints)


class MetaSplice(type):
    """
    Metaclass to override __call__ to remove trusted and synthesized keyword parameters.
    We can probably also do this in __new__ instead (and set the trusted and synthesized
    attributes in __new__ as well). A trusted flag is used to identify if an object is
    trusted and a synthesized flag to identify if an *untrusted* object is synthesized.
    An object *cannot* be both trusted and synthesized.

    The new object's taint is the union of all taints of its arguments, and the taints
    keyword parameter which is optional (default is no taint).
    """

    def __call__(cls, *args, **kwargs):
        # __new__ will not be decorated by to_splice_cls()
        # so we must set the trusted and synthesized flags
        # based on the args and kwargs afterwards here. We
        # do not want to decorate __new__ because deepcopy()
        # which is used in the decorator calls __new__. As
        # such, we would create an infinite recursion!
        obj = cls.__new__(cls, *args, **kwargs)
        untrusted, synthesized = contains_untrusted_arguments(*args, **kwargs)
        obj = SpliceMixin.to_splice(obj, not untrusted, synthesized, None)
        # Object construction may also set
        # the flags explicitly in "kwargs".
        trusted = None
        synthesized = None
        if "trusted" in kwargs:
            trusted = kwargs["trusted"]
            del kwargs["trusted"]
        if "synthesized" in kwargs:
            synthesized = kwargs["synthesized"]
            del kwargs["synthesized"]
        # Object construction may also set
        # taint explicitly in "kwargs".
        taints = None
        if "taints" in kwargs:
            taints = kwargs["taints"]
            del kwargs["taints"]

        obj.__init__(*args, **kwargs)

        # If flags have also been set explicitly,
        # we have to make sure there is no conflict.
        # One can set a trusted object explicitly to
        # untrusted and a non-synthesized object to
        # synthesized but not the other way around.
        if trusted is not None:
            if not trusted:
                # Regardless of what the original flag was,
                # we can always overwrite it with untrusted
                obj._trusted = trusted
            else:
                if not obj._trusted:
                    # We have previously determined that the
                    # object should not be trusted, overwrite
                    # an untrusted object with a trusted flag
                    # raise an AttributeError.
                    raise AttributeError("Splice has determined that the object is untrusted,"
                                         " but you are trying to manually set the flag otherwise.")
        # Similar treatment for the synthesized flag.
        if synthesized is not None:
            if synthesized:
                obj._synthesized = synthesized
            else:
                if obj._synthesized:
                    raise AttributeError("Splice has determined that the object is synthesized,"
                                         " but you are trying to manually set the flag otherwise.")
        # Final check to make sure flag values make sense
        if obj._trusted and obj._synthesized:
            raise AttributeError("Cannot initialize a trusted and synthesized object.")
        # Object taint update
        obj._taints = union_argument_taints(*args, **kwargs)
        if taints is not None:
            obj._taints |= taints
        return obj


class SpliceMixin(metaclass=MetaSplice):
    """
    A Mixin class for adding both untrustiness and trust-awareness
    to an existing Python class (built-in or user-defined).

    Important note: for __init_subclass__'s to_splice_cls() to work
    SpliceMixin must used as the *first* parent class in a subclass.
    """

    registered_cls = {}

    def __new__(cls, *args, trusted=True, synthesized=False, taints=None, **kwargs):
        """
        We must override __new__ so that "trusted" and "synthesized"
        don't flow into the super().__new__, which can be bad for
        base classes that are not designed for inheritance.

        We do the same for "taints" as well.
        """
        # Because we override __new__, if super() is object, then __new__
        # does not take any additional arguments. Here are some references:
        # https://stackoverflow.com/a/65862579/9632613
        # https://stackoverflow.com/a/19725350/9632613
        if super().__new__ is object.__new__:
            self = super().__new__(cls)
        else:
            self = super().__new__(cls, *args, **kwargs)
        return self

    def __init_subclass__(cls, **kwargs):
        """
        Whenever a class inherits from this, this special method is called on the cls,
        so that we can change the behavior of subclasses. This is closely related to
        class decorators, but where class decorators only affect the specific class
        they’re applied to, __init_subclass__ solely applies to future subclasses of
        the class defining the method. Here we use both __init_subclass__ and class
        decorator, so a subclass of SpliceMixin and its subclasses can be decorated.
        """
        SpliceMixin.to_splice_cls(cls)
        SpliceMixin.register(cls)

    # def __str__(self):
    #     if not self.trusted:
    #         raise TypeError("cannot use str() or __str__ to coerce an untrusted value to str. "
    #                         "Use to_trusted() instead.")
    #     else:
    #         return SpliceMixin.registered_cls["str"](super().__str__())
    #
    # def __repr__(self):
    #     if not self.trusted:
    #         raise TypeError("cannot use repr() or __repr__ to coerce an untrusted value to str. "
    #                         "Use to_trusted() instead.")
    #     else:
    #         return SpliceMixin.registered_cls["str"](super().__repr__())
    #
    # def __format__(self, format_spec):
    #     if not self.trusted:
    #         raise TypeError("cannot use format() or __format__ to coerce an untrusted value to str. "
    #                         "Use to_trusted() instead.")
    #     else:
    #         return SpliceMixin.registered_cls["str"](super().__format__(format_spec))

    def __iter__(self):
        """Define __iter__ so the iterator returns a splice-aware value."""
        for x in super().__iter__():
            yield SpliceMixin.to_splice(x, self.trusted, self.synthesized, self.taints)

    # def __deepcopy__(self, memo):
    #     """
    #     Override __deepcopy__ so that when deepcopy() is invoked in to_splice_cls(),
    #     this method is called. Ref: https://stackoverflow.com/a/15774013/9632613.
    #     """
    #     cls = self.__class__
    #     result = cls.__new__(cls)
    #     memo[id(self)] = result
    #     for k, v in self.__dict__.items():
    #         setattr(result, k, copy.deepcopy(v, memo))
    #     return result

    @staticmethod
    def to_splice(value, trusted, synthesized, taints):
        """
        Convert a value to the splice-aware type if
        it exists. The flags will be set based on
        "trusted" and "synthesized". If there exists
        no corresponding Splice-aware type, we raise
        a warning. If value is already Splice-aware, this
        function can be used to modify its flags.

        "Taints" are handled similarly.
        """
        # If value is already a splice-aware type
        if isinstance(value, SpliceMixin):
            value.trusted = trusted
            value.synthesized = synthesized
            value.taints = taints
            return value
        # bool is a subclass of int, so we must check it first
        # it cannot be usefully converted to a splice-aware type
        elif isinstance(value, bool):
            return value
        # Conversion happens here. We only know how to convert
        # classes that are registered (i.e., classes that subclass
        # SpliceMixin, which automatically registers the class)
        cls = value.__class__.__name__
        if cls in SpliceMixin.registered_cls:
            return SpliceMixin.registered_cls[cls].splicify(value, trusted, synthesized, taints)
        #####################################################
        #  Recursively convert values in list or other structured data
        #  Note that we do not just use list/dict/set comprehension as
        #  we do not want this function to create a new list/dict/set
        #  object since lists/dicts/sets are mutable and may be passed
        #  around in recursive functions to be mutated.
        elif isinstance(value, list):
            for i in range(len(value)):
                value[i] = SpliceMixin.to_splice(value[i], trusted, synthesized, taints)
            return value
        elif isinstance(value, tuple):
            # Creating a new tuple is fine because tuple is immutable
            return tuple(SpliceMixin.to_splice(v, trusted, synthesized, taints) for v in value)
        # Cannot modify a set during iteration, so we do it this way:
        elif isinstance(value, set):
            list_copy = [SpliceMixin.to_splice(v, trusted, synthesized, taints) for v in value]
            value.clear()
            value.update(list_copy)
            return value
        # Cannot modify a dict during iteration, so we do it this way:
        elif isinstance(value, dict):
            dict_copy = {SpliceMixin.to_splice(k, trusted, synthesized, taints):
                         SpliceMixin.to_splice(v, trusted, synthesized, taints)
                         for k, v in value.items()}
            value.clear()
            value.update(dict_copy)
            return value
        # TODO: Perhaps we should raise an error instead.
        else:
            warnings.warn("{value} (of type {type}) has no splice-aware type defined".format(value=value,
                                                                                             type=type(value)),
                          category=RuntimeWarning,
                          stacklevel=2)
            return value

    @staticmethod
    def to_splice_cls(cls):
        """
        A class decorator that decorates all methods in a cls so that
        they return either trusted or untrusted value(s). If cls is a
        subclass of some base classes, then we want methods in base
        classes to be able to return (un)trusted value(s) as well.

        Important note: Any cls (i.e., SpliceX) method to be decorated
        must start with either "splice_" or "_splice_" (for protected
        methods), while base class methods have no such restriction (as
        it is likely that developers have no control over those). Using
        this convention, developers can prevent base class methods
        from being decorated by overriding the method (and then just call
        the base class method in the override method). If, for example,
        the developer needs to override a special "dunder" method, and
        the overridden method needs to be decorated, they should first
        implement a helper method '_splice__XXX__' and then call the
        helper method in the special method. As such, _splice__XXX__
        will be decorated (and therefore the calling special method).
        """

        def to_splice_method(func):
            """
            A function decorator that makes the original function (that
            may not be trust-aware) return (un)trusted value(s) if possible.
            """

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Calling inherited methods (including built-in methods) - IMPORTANT NOTE:
                # res usually return objects of original (including built-in) type(s), but
                # it is possible that res returns objects of Splice-managed types already.

                # TODO: does it *always* make sense to consider the return value/self
                #  untrusted/synthesized/tainted as long as any one of the input is?
                untrusted, synthesized = contains_untrusted_arguments(*args, **kwargs)
                taints = union_argument_taints(*args, **kwargs)
                # Check if "self" (i.e., the first argument) is modified
                # Note that this check applies only to methods that are
                # not a class method or a static method, because otherwise
                # the first argument is not "self"!
                is_static = is_static_method(cls, func.__name__)
                is_class = is_class_method(cls, func.__name__)
                # We must use deep copy so that it actually holds a copy
                # of the original "self", not just a reference. This is
                # important for mutable objects.
                self = copy.deepcopy(args[0])
                # Execution the original method
                res = func(*args, **kwargs)
                # If in-place updates occurred in func, then the object
                # referenced by args[0] will be different from the
                # original copy. Note that for immutable objects, this
                # should never be the case!
                if not is_static and not is_class and self != args[0]:
                    # "self" should be splice-aware
                    # FIXME: This may not be true for user-defined classes
                    if not isinstance(args[0], SpliceMixin):
                        raise RuntimeError("{} is not Splice-aware.".format(args[0]))
                    # See if "self" should be an untrusted and/or synthesized object.
                    if untrusted:
                        args[0].trusted = False
                    if synthesized:
                        args[0].synthesized = True
                    # Update "self"'s taints
                    if args[0].taints is None:
                        args[0].taints = taints
                    else:
                        args[0].taints |= taints
                # Some quick return (nothing else to do)
                if res is None or res is NotImplemented or isinstance(res, SpliceMixin):
                    return res
                return SpliceMixin.to_splice(res, not untrusted, synthesized, taints)

            return wrapper

        # set of callable method names already been decorated/inspected
        handled_methods = set()
        # First handle all methods in cls class
        # TODO: __dict__ does not return __slots__, so will
        #  not work if cls uses __slots__ instead of __dict__
        # NOTE: Do NOT use __dict__[key] to test callable(), use getattr() instead. Not because
        # of performance, but for more important reasons! For example, callable(__dict__["__new__"])
        # returns False because it is a class method (in fact, all static and class methods will
        # return False if use __dict__ instead of getattr() to obtain the method! Reference:
        # https://stackoverflow.com/questions/14084897/getattr-versus-dict-lookup-which-is-faster
        for key in cls.__dict__:
            # Only callable methods are decorated
            value = getattr(cls, key)
            if not callable(value):
                continue
            # All callable methods are inspected in cls
            handled_methods.add(key)
            # Decorate only 'splice_' or '_splice_' prefixed methods in cls.
            if key.startswith("splice_") or key.startswith("_splice_"):
                setattr(cls, key, to_splice_method(value))
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
        # (the first being cls and the second being SpliceMixin).
        # SpliceMixin should *not* be decorated, so add them all in handled_methods
        mixin_cls = cls.__mro__[1]  # IMPORTANT: SpliceMixin MUST be the second class in MRO!
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
                # Delegate to_splice_method() to handle other cases
                # since there is not much convention we can specify.
                # Note that it is possible to_splice_method() can just
                # return the same method output without any changes.
                # Note also that we are adding those attributes to cls!
                # Therefore, once decorated by to_splice_method(),
                # cls will always call the decorated methods (since they
                # will be placed at the front of the MRO), not the ones
                # in any of the base classes!
                setattr(cls, key, to_splice_method(value))
        # NOTE: The new MRO after decoration (when called from SpliceX) --
        # 1. Original cls (SpliceX) methods (decorated and non-decorated) and
        #    all decorated methods.
        # 2. All methods defined in SpliceMixin.
        # 3. All other non-decorated methods from classes other than SpliceX
        #    and SpliceMixin following the original MRO.
        return cls

    def to_trusted(self, forced=False):
        """
        Set the trusted flag of a value to be True. Conversion results in
        a RuntimeError if the value is synthesized, unless 'forced' is set
        to be True. If 'forced' is True, conversion always works. Because
        the value is trusted, the synthesized flag of the value is False.
        """

        if self.synthesized and not forced:
            raise RuntimeError("cannot convert a synthesized value to a trusted value")
        else:
            self.trusted = True
            self.synthesized = False
            return self

    @staticmethod
    def register(cls):
        """Register the Splice class with its inherited counterpart so conversion can be automated."""

        orig = cls.__mro__[2]  # IMPORTANT: the inherited (including built-in) class MUST be the third class in MRO!
        SpliceMixin.registered_cls[orig.__name__] = cls

    @property
    def synthesized(self):
        return self._synthesized

    @synthesized.setter
    def synthesized(self, synthesized):
        self._synthesized = synthesized

    @property
    def trusted(self):
        return self._trusted

    @trusted.setter
    def trusted(self, trusted):
        self._trusted = trusted

    @property
    def taints(self):
        return self._taints

    @taints.setter
    def taints(self, taints):
        self._taints = taints

    @classmethod
    def splicify(cls, value, trusted, synthesized, taints):
        """
        Convert a value to its splice-aware type and set the flags. Reclassing an object
        by assigning __class__ does *not* always work because __class__ assignment is only
        supported for heap types or ModuleType subclasses. This approach is simple and general
        enough to support most user-defined classes but not so much for immutable objects
        that are not allocated on the heap. For such cases, we must override this method."""
        try:
            value.__class__ = cls
            value.trusted = trusted
            value.synthesized = synthesized
            value.taints = taints
            return value
        except TypeError as e:
            raise NotImplementedError("You cannot inherit splicify() from SpliceMixin for this class;"
                                      "instead you should override the splicify() method to convert"
                                      "a value to its splice-aware type and set the flags accordingly."
                                      "The original error as a result of inheritance is: \n{}".format(e))
