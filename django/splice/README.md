### To-Do's:
* [ ] The `bool` type cannot be subclassed (unlike `int` or `float`, for example).
  This means that, for any function that returns a `bool`, we cannot coerce the
  return value to an *untrusted* type even if the input to the function is untrusted.
  Affected built-in functions include:
    * `all()`
    * `any()`
    * `bool()`

* [x] Some built-in functions enforce their return type, even though they can be
  overridden by their respective magic method. We raise `TypeError` if input to
  those functions are *untrusted* to prevent unintended or illegal coercion to
  trusted data. Note that there is *no* type coercion if one calls the magic
  method equivalents directly (with exceptions), but since we do not want to
  override built-in functions directly (which may causes unintended side effects),
  we cannot enforce `TypeError` without changing magic methods.
    * `str()` (`__str__`):  must return a string; otherwise `TypeError`. `TypeError`
      is directly raised from the language runtime, so we do not need to raise
      `TypeError` in `__str__`. `__str__` must also return a string.
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

* [ ] Some built-in types are not (yet) handled by Splice.
    * `bytearray`
    * `bytes`
    * `bool`: cannot be handled by subclassing (see above).
    * `complex`
    * `dict`

* [ ] Some built-in functions are not yet handled by Splice.
    * `compile()`


### Notes
* The following built-in functions work as intended or need not be handled:
    * `abs()`: untrusted input returns untrusted output
      (e.g., `UntrustedFloat` -> `UntrustedFloat`).
    * `breakpoint()`: for debugging; no special handling needed.
    * `callable()`: test whether input appears callable. Since only non-callable
      data can be synthesized, this built-in function should always return `False`
      for trusted and untrusted data anyways.
    * `delattr()`: delete the named attribute; no special handling needed.
    * `dir()`: return a list of valid attributes/names. Its corresponding magic
      method `__dir__` needs no special handling either.

### Customize a Synthesizer
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
    def to_float(self, value):
        # Convert value (a datetime object) to float.

    def to_python(self, value):
        # Override FloatSynthesizer's to_python() to
        # convert value (a float object) back to a
        # datatime object and return an untrusted value.

    def simple_synthesis(self, value):
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

Now that you have both `DatetimeSynthesizer` and `UntrustedDatetime`, the last step
is to modify `init_synthesizer()` in synthesis.py:
```angular2html
def init_synthesizer(value, vectorized=False):
    ...
    # Simply adding the following elif branch does the job:
    elif isinstance(value, UntrustedDatetime):
        return DatetimeSynthesizer()
    ...
```
