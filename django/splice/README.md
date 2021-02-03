# Customize a Synthesizer
Splice has a number of built-in synthesizers (e.g., `IntSynthesizer`, `FloatSynthesizer`,
`BitVecSynthesizer`, `StrSynthesizer`) that can synthesize different types of
values (e.g., `int`, `str`, and `float`). All synthesizers subclass from the base
class `Synthesizer` and output corresponding *untrusted* data (of type e.g.,
`UntrustedInt`, `UntrustedFloat`, and `UntrustedStr`). With these fundamental
type classes, you can (in most cases) easily create a new synthesizer for a
different type (class) of objects, leveraging existing synthesizers. For example,
to create a synthesizer that synthesizes Python's `datetime` objects, you can:
1. Create a new synthesizer class `DatetimeSynthesizer` that inherits from
   `FloatSynthesizer`.
2. Add a new function that converts a `datetime` object to a `float` object, e.g.,
   using `datetime`'s `timestamp()` function.
3. Override `to_python()` to convert the synthesized float value back to a `datetime`
   object and convert the `datetime` object to its untrusted type (see below).
4. Override `simple_synthesis()` to return untrusted and synthesized `datetime` object.

The code would look like this:
```angular2html
class DatetimeSynthesizer(FloatSynthesizer):
    @staticmethod
    def to_float(value):
        # Convert value (a datetime object) to float.

    @staticmethod
    def to_python(value):
        # Override FloatSynthesizer's to_python() to
        # convert value (a float object) back to a
        # datetime object and return an untrusted value.

    @staticmethod
    def simple_synthesis(value):
        # Override FloatSynthesizer's simple_synthesis()
        # to return an untrusted datetime object with
        # the synthesized flag set to True.
```
When a `datetime` object needs to be synthesized, simply call `to_float()` first
to convert the value to `float` and then use `DatetimeSynthesizer`
like a `FloatSynthesizer`.

Notice that `to_python()` and `simple_synthesis()` should return an untrusted
`datetime` object, not Python's original `datetime` object. This can also be
done by subclassing both `UntrustedMixin` and `datetime` to create a new class.
The most basic construction looks similar to this:
```angular2html
class UntrustedDatetime(UntrustedMixin, datetime):
    def __new__(cls, *args, synthesized=False, **kwargs):
        """We need to define __new__ because datetime is immutable!"""
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)
```
An `UntrustedDatetime` object will now behave exactly the same as a regular
`datetime` object except that it has an additional `synthesized` attribute.
All methods in `UntrustedDatetime` are now decorated versions of the ones in
`datetime`, which output untrusted values. If some methods should not output
untrusted values, you can easily override them in `UntrustedDatetime`:
```angular2html
class UntrustedDatetime(UntrustedMixin, datetime):
    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    def timestamp():
        # We simply call datetime's timestamp to override
        # the method so that timestamp() output will not
        # be an untrusted value (note that this is just an
        # example; you probably don't want to override this
        # method at all).
        return super().timestamp()
```
You would return an `UntrustedDatetime` object in `DatetimeSynthesizer`'s
`to_python()` and `simple_synthesis()` methods.

Note that `DatetimeSynthesizer` and `UntrustedDatetime` are implemented in
synthesis.py and untrustedtypes.py for reference.

# Trusted Sinks
Trusted data sinks are locations in the framework that allow only non-synthesized
data (although data *can* be untrusted).
## Views
According to Django's official documentation:
> A view function, or view for short, is a Python function that takes a
> Web request and returns a Web response. This response can be the HTML
> contents of a Web page, or a redirect, or a 404 error, or an XML
> document, or an image...or anything, really. The view itself contains
> whatever arbitrary logic is necessary to return that response.

Since the output of a view is a response to the user, we consider views
(or more concretely, *responses* returned by views) to be trusted data sinks.
In general, regardless of the implementation of views (i.e., function-based
or class-based), views typically return two types of responses:
1. `HttpResponse`: Standard `HttpResponse` objects are static structures. The
   *content* of the response, which would be rendered to the user, is a
   bytestring encoded from a string if necessary. The content must contain only
   trusted data. Since Splice checks and stops illegal coercion from any
   untrusted data, including synthesized data, to trusted data through `str()`
   (as well as other built-in functions such as `int()` and `float()`,
   and functions that uses `__str__` such as `print()` and `format()`),
   the developer must *explicitly* perform untrusted-to-trusted data conversion
   through `to_trusted()` call. Therefore, Splice effectively enforces that
   the developer checks potentially untrusted data before sending data to the
   sink; otherwise, `HttpResponse` cannot be rendered.
2. `TemplateResponse`: From Django's official documentation (also see below),
   `TemplateResponse` allows decorators or middleware to modify a response
   after it has been constructed by the view. Splice middleware checks the
   *context* of the response right before the response is rendered. Response
   context is the abstraction where dynamic user data is stored and therefore
   is where untrusted (and synthesized data) might leak into the trusted sink
   that is the `TemplateResponse`. `TemplateResponse` and its equivalent are
   what the developer typically uses to render their content dynamically.

> Unlike basic `HttpResponse` objects, `TemplateResponse` objects retain the
> details of the template and context that was provided by the view to compute
> the response. The final output of the response is not computed until it is
> needed, later in the response process.

Django also defines a shortcut function `render()` that works just like
`TemplateResponse` but constructs response context and renders `HttpResponse`
directly. This is originally designed to circumvent potentially costly
middleware inspection and context modification. To prevent untrusted and
synthesized data leakage, we decorate `render()` to create an additional
data checkpoint. The decorator works the same way as the middleware and
is only used for the shortcut.

# Notes
* The following built-in functions work as intended or need not be handled:
    * `abs()`: untrusted input returns untrusted output
      (e.g., `UntrustedFloat` -> `UntrustedFloat`).
    * `breakpoint()`: for debugging; no special handling is needed.
    * `callable()`: test whether input appears callable. Since only non-callable
      data can be synthesized, this built-in function should always return `False`
      for trusted and untrusted data anyways.
    * `delattr()`: delete the named attribute; no special handling is needed.
    * `dir()`: return a list of valid attributes/names. Its corresponding magic
      method `__dir__` needs no special handling either.
    * `divmod()`: untrusted input returns untrusted output.
    * `enumerate()`: untrusted input returns untrusted output.
    * `eval()`: untrusted input returns untrusted output.
    * `exec()`: untrusted input returns untrusted output.
    * `filter()`: untrusted input returns untrusted output.
    * `frozenset()`: untrusted input returns untrusted output.
    * `getattr()`: return the value of the named attribute of an object;
      no special handling is needed.
    * `globals()`: return a dictionary representing the current global symbol
      table; no special handling is needed.
    * `hasattr()`: whether an object has the named attribute;
      no special handling is needed.
    * `help()`: invoke the built-in help system; no special handling is needed.
    * `id()`: return the “identity” of an object; no special handling is needed.
    * `input()`: no special handling is needed.
    * `isinstance()`: whether an object is an instance of a class;
      no special handling is needed.
    * `issubclass()`: subclass relation check; no special handling is needed.
    * `iter()`: return an iterator object; no special handling is needed.
    * `list()`: we need only elements in the list to be untrusted, so no special
      handling is needed on the list object itself.
    * `locals()`: update and return a dictionary representing the current local
      symbol table; no special handling is needed.
    * `map()`: apply a function to every element in an iterable. The function
      needs to decorate its output, but not `map()`.
    * `max()`: untrusted input returns untrusted output.
    * `memoryview()`: no special handling is needed.
    * `min()`: untrusted input returns untrusted output.
    * `next()`: retrieve the next item from the iterator; no special handling
      is needed.
    * `open()`: open a file and return a file object; no special handling is needed.
    * `pow()`: untrusted input returns untrusted output.
    * `reversed()`: return a reverse iterator; no special handling is needed.
    * `round()`: untrusted input returns untrusted output.
    * `set()`: we need only elements in the set to be untrusted, so no special
      handling is needed on the set object itself.
    * `setattr()`: assign the value to the attribute of an object; like
      `getattr()`, no special handling is needed.
    * `slice()`: untrusted input returns untrusted output.
    * `sorted()`: untrusted input returns untrusted output.
    * `sum()`: untrusted input returns untrusted output.
    * `super()`: return a proxy object that delegates method calls to a parent
      or sibling class; no special handling is needed.
    * `tuple()`: we need only elements in the tuple to be untrusted, so no special
      handling is needed on the tuple object itself.
    * `type()`: no special handling is needed.
    * `vars()`: return the `__dict__` attribute; no special handling is needed.
    * `zip()`: untrusted input returns untrusted output.
    * `__import__`: invoked by the import statement; no special handling is needed.

* `len()` is decorated through built-in function override during *import*. This
  is done in `__init__.py`. Overriding functions in the builtin module is risky
  since all Python modules use the builtin module. For example, we encounter
  issues when attempting to override `int()` and `float()`.

* We considered Python's *type hints* as a language feature to enforce trusted
  data sinks, for example, by explicitly declaring only the (trusted) types of
  input that are acceptable by a data structure. However, the Python runtime
  does not enforce function and variable type annotations.

# To-Do's:
* [ ] The `bool` type cannot be subclassed (unlike `int` or `float`, for example).
  This means that, for any function that returns a `bool`, we cannot coerce the
  return value to an *untrusted* type even if the input to the function is untrusted.
  Affected built-in functions include:
    * `all()`
    * `any()`
    * `bool()`

  In fact, similar to `str()` and `__str__`, `__bool__` and `bool()` **cannot**
  return any other type but `bool`; otherwise, you will receive a `TypeError`.
  This is enforced by the language runtime and cannot be circumvented. However,
  unlike `str()` (see below), we cannot simply just let `TypeError` to be raised
  since doing so affects many other operators than casting to `bool()`. On the
  other hand, we suspect that failure to having an `UntrustedBool` type causes
  issues related to *control-flow-based trustworthiness propagation* only
  (analogous to control-flow-based under-tainting).

* [x] Some built-in functions enforce their return type, even though they can be
  overridden by their respective magic method. We raise `TypeError` if input to
  those functions are *untrusted* to prevent unintended or illegal coercion to
  trusted data. Note that there is *no* type coercion if one calls the magic
  method equivalents directly (with exceptions), but since we do not want to
  override built-in functions directly (which may causes unintended side effects),
  we cannot enforce `TypeError` without changing magic methods.
    * `str()` (`__str__`):  must return a string; otherwise `TypeError`. `TypeError`
      is directly raised from the language runtime, so we do not need to raise
      `TypeError` in `__str__`. `__str__` must also return a string. `print()`
      calls `__str__`, and therefore is similarly handled.
    * `repr()` (`__repr__`): same as `str()` (`__str__`).
    * `int()` (`__int__`): coerce to `int` if returns a subclass of `int`.
      `__int__` does not enforce coercion, but we must raise `TypeError` in
      `__int__` to override `int()`.
    * `float()` (`__float__`): coerce to `float` if returns a subclass of `float`.
      `__float__` does not enforce coercion, but we must raise `TypeError` in
      `__float__` to override `float()`.
    * `complex()` (`__complex__`): we cannot yet handle `complex` built-in type.
      However, `complex()` can delegate to `__complex__` (if defined), and then
      `__float__` (if defined), and finally `__index__`. Therefore, if the
      untrusted input is delegated to ``__float__``, `TypeError` will be raised.

* [ ] Some built-in functions have no corresponding magic methods, or they may
  call some magic methods as helper functions (e.g., `bin()` calls `__index__`,
  if input is not a Python `int` object, to get the input object's integer
  representation). They also enforce their return type, but it is not clear that
  semantically we should simply raise `TypeError` like we do before.
    * `ascii()`: always return a string.
    * `bin()`: always return a binary string prefixed with `0b`.
    * `chr()`: always return a string.
    * `hash()`: while `__hash__()` returns an UntrustedInt object, `hash()`
      always returns an integer.
    * `hex()`: always return a string.
    * `oct()`: always return a string.
    * `ord()`: take only a string as input (but not `UntrustedStr`) and return
      a string.

* [ ] Some built-in types are not (yet) handled by Splice.
    * `bytearray`
    * `bytes`
    * `bool`: cannot be handled by subclassing (see above).
    * `complex`
    * `dict`

* [ ] Some built-in functions are not yet handled by Splice.
    * `compile()`
    * `format()`
    * `range()`

* [ ] Go through magic methods and identify ones that should not be
  decorated by `add_synthesis_to_func()` in `untrustedtypes.py`.
