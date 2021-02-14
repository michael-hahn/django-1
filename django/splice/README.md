# Untrusted Data Types
Splice introduces **untrusted** data types and leverages the type system to
propagate *untrustiness*. A piece of data is untrusted if 1) its value is provided
by an untrusted source (e.g., a remote user from a network socket), or 2) its value
might be reassigned by Splice (i.e., when Splice performs *deletion-by-synthesis*).
Untrustiness propagates when untrusted data interacts with other untrusted or
trusted data, in a fashion similar to classic taint propagation. For example, in
an assignment-after-addition operation `z = x + y`, `z` becomes untrusted if and
only if at least one operand (i.e., either `x` or `y`, or both) is untrusted.

With the introduction of untrusted data types, Splice further leverages the type
system to force programmers to use **defensive programming**. Defensive programming
is essential for programs containing untrusted data, because any unchecked use
of such data can cause harm to the program or even the underlying system (e.g.,
SQL injection caused by malicious input from the network), or return bogus values.

## [Python Background](#python-background)
Everything (e.g., literals, classes, functions) in Python is an *object* and every
object has a *type*, which is defined by a *class*. The type of object
determines the *methods* that are available to call on that object. Those methods
are defined in the class, and because Python supports multi-inheritance, which
allows a class to subclass from multiple base classes, methods defined in the
base classes can be inherited (or overridden) by the subclass. Every class also
has a set of predefined *special methods*, as specified by Python's **data model**,
that enrich customized classes with language features to emulate operations of
built-in types (i.e., Python's approach to *operator overloading*). These special
methods' names are all prefixed and affixed by two underscores and therefore
often referred to as "dunder" (double-underscore) methods. For example, to allow
a customized class to emulate the addition operation (`+`) of numeric types
(e.g., `int`), Python has a special method `__add__`. If the customized class
defines `__add__`, Python invokes this method when the class' objects are being
summed together.

Special methods involving *binary arithmetic operations* (e.g., `+`, `-`, and ``<<``)
also have their corresponding *reflected* special method with an additional "r"
prefixed in its method name (e.g., `__radd__` is `__add__`'s reflected counterpart).
The reflected method is called 1) if the operands are of different types, and the
left operand does not define the non-reflected method, or 2) if the right operand’s
type is a *subclass* of the left operand’s type and that subclass has a different
implementation of the reflected method (instead of inheriting the reflected method
from the base class). For example, when evaluating the expression `x + y`, if `x`
and `y` are of two different types, `y.__radd__(x)` is called if `x.__add__(y)`
is not implemented. On the other hand, if `y`'s type is a subclass of `x`'s type,
then `x.__add__(y)` is called if `y.__radd__(x)` is not implemented. This latter
case allows a subclass to override its ancestors’ operations (without forcing
the object of the subclass to always be the left operand).

As mentioned above, special methods are Python's approach to operator overloading,
which in fact includes *built-in functions* such as `int()`, `float()`, and `str()`
that construct objects of their respective *built-in types*. For example, if the
class of an object `x` defines `__int__`, `int(x)` invokes `x.__int__()`. However,
Python restricts the return type of those built-in functions, even though they can
be customized by special methods (and no restriction is placed on those special
methods). For example, while a class can customize `__int__`, it *must* return
an object of type `int` for `int()` to run correctly; any non-`int` return value
(including that of an `int` subclass) leads to a type error (or forced coercion
to `int` with a warning).

> The following built-in functions have strict return types. Their respective
> special method can override them but must return the right type:
> 1. `int()` (special method: `__int__`) must return an object of type `int`. The
>    ability to return an instance of a strict subclass of `int` is deprecated and
>    will be coerced to `int` with a deprecation warning.
> 2. `float()` (special method: `__float__`) must return an object of type `float`.
>    The ability to return an instance of a strict subclass of `float` is
>    deprecated and will be coerced to `float` with a deprecated warning.
> 3. `str()` (special method: `__str__` or possibly `__repr__`) must return an
>    object of type `str` *or its subclass*.
> 4. `repr()` (special method: `__repr__`) must return an object of type `str`
>    *or its subclass*.
> 5. `format()` (special method: `__format__`) must return an object of type `str`
>    *or its subclass*.
> 6. `hash()` (special method: `__hash__`) must return an `int` object.
> 7. `len()` (special method: `__len__`) must return an `int` object.

## Splice in Python
Splice's untrusted data types are constructed from regular Python classes
but with an additional boolean *attribute* `synthesized`,  which signals whether
Splice has reassigned the value through synthesis. We will call Python classes
*not* under the influence of Splice "native classes" henceforth. Built-in types
and any existing customized class without Splice's "intervention" are native
classes. For example, Python's built-in type `int` (a native class) has an
untrusted counterpart called `UntrustedInt`. A customized class can also have
its own untrusted type. While an object of an untrusted type behaves just like
its native counterpart (i.e., has the same of methods defined), untrusted data
types should not be considered equivalent to their corresponding native classes
due to the semantic difference as the result of untrustiness. As such, to make
this difference explicit and to assist defensive programming, Splice forbids type
coercion through built-in functions such as `int()` and `str()` (which drop
untrustiness) by overriding their corresponding special methods. Instead, if
granting trust to an object of an untrusted type is warranted, the programmer
must call `to_trusted()` to make their intent explicit.

Untrustiness cannot be propagated properly in a program if untrusted data types
are the only classes that propagate untrustiness. For example, an `int` object
can be created through a list of bytes by calling the `int` type's `from_bytes()`
method. If the bytes are untrusted, we would expect the resulting `int` object
to be untrusted as well. However, since the native (i.e., built-in) `int` class
is not *trust-aware*, the resulting object would be of the native `int` type,
stopping any future untrustiness propagation. To address this issue, Splice also
provides a tool that constructs **trust-aware** data types from native classes.
Trust-aware classes are just like untrusted classes except that objects of a
trusted-aware class is considered to be *trusted*, and it can properly handle
untrustiness propagation. Using the same `from_bytes()` example, a trust-aware
`int` class (called `TrustAwareInt`) creates an `UntrustedInt` object if any
byte in the input is untrusted. If, on the other hand, none of the bytes are
untrusted, a `TrustAwareInt` object is created. The `TrustAwareInt` object
will continue handling untrustiness propagation properly in future operations
on the object.

A Python program running on top of Splice runs just like a regular Python program
without Splice, except that:
1. All native classes in the program must be replaced by one untrusted and one
   trust-aware class. As such, operations between objects propagate untrustiness.
   For example, the output of most operations involving one or more objects of
   untrusted types is of an untrusted type. Splice provides tools to easily
   convert any native classes to untrusted and trust-aware classes; many built-in
   types have already been converted by Splice.
   > Not all operations propagate or should propagate untrustiness, see
   > [Technical Details](#technical-details).
2. As mentioned, the programmer should practice **defensive programming**,
   especially when objects of untrusted types are involved. At times, Splice also
   leverages Python's type system to enforce proper handling of untrusted objects,
   for example, at [trusted sinks](#trusted-sinks) where only objects of
   trust-aware types are allowed.

### [Technical Details](#technical-details)
Splice leverages class inheritance to provide convenience to define new untrusted
and trust-aware types from existing native Python classes. The framework itself
also provides untrusted and trust-aware built-in types (e.g., `int` and `str`).

#### Build Untrusted Data Types Through Inheritance
Splice provides an `UntrustedMixin` class that contains most logic needed for new
untrusted types. To create an untrusted type, the programmer should inherit both
`UntrustedMixin` and the corresponding native Python class. All untrusted data
types conventionally have the prefix `Untrusted` in their class names (and use
camel case following also Python's naming convention). For example, `UntrustedInt`
is defined as:
```python
from django.splice.utils import UntrustedMixin
class UntrustedInt(UntrustedMixin, int):
    pass
```
Note that `UntrustedMixin` must be inherited before `int`. We use the integer
type as the running example for the rest of this document. See
[Create a New Untrusted Class](#create-a-new-untrusted-class) for a different
example.

One important task of `UntrustedMixin` is decorating the output of methods
(including those inherited from the native Python class) invoked by an object
of an untrusted type to be untrusted, since most operations involving such an
object should return untrusted values. Specially, once a new untrusted class
inherits `UntrustedMixin`, it would call `__init_subclass__` (a Python special
method) to decorate methods defined in the new untrusted class and all of
its base classes following its MRO (skipping `UntrustedMixin` itself). MRO, or
method resolution order, is the way Python resolves a method in an object's
class's inheritance chain. All decorated methods become the attributes of the new
untrusted class and therefore are no longer resolved from the base classes in
which they were originally defined. The decoration process follows the following
order:
1. Callable methods defined in the new untrusted class are first considered.
   Since the programmer has the full control of this class, it is technically *not*
   necessary for Splice to decorate any methods (or overridden methods). Instead,
   *this class is where the programmer could prevent some inherited methods from
   being automatically decorated by `UntrustedMixin` through overriding*. In case
   that the programmer wants a method to be automatically decorated, Splice
   stipulates that the method name must be prefixed by either `untrusted_` or
   `_untrusted_`. However, the programmer can always implement the method to
   directly return an untrusted value (if needed) and not follow this naming
   convention.
2. All methods in `UntrustedMixin` will not be decorated since they are handled
   directly by Splice.
3. Callable methods in the base classes are then considered. To ensure that
   decorated methods are the ones that would have been resolved in the MRO,
   decoration follows MRO, and methods that have been decorated will not be
   considered again if they appear again later in the MRO (this rule also
   applies to methods that Splice have already encountered in (1) and (2)).

Therefore, after the decoration process is finished, the new MRO will be:
1. All defined methods in the untrusted class (both decorated and non-decorated)
   and all decorated methods from all the base classes
2. All methods defined in `UntrustedMixin`
3. All other non-decorated methods from classes other than the untrusted class
   and `UntrustedMixin`, resolved by the original MRO.

> Some methods and special methods provide functionality that should not
> propagate untrustiness. That is, they should not return untrusted values
> and therefore are not decorated.
> <details>
> <summary>List of Non-decorated Methods</summary>
> Special methods that create, initialize, or destroy class instances:
>
> 1. `__new__`
> 2. `__init__`
> 3. `__del__`
>
> Special methods that control attribute access for class instance:
> 1. `__getattr__`
> 2. `__getattribute__`
> 3. `__setattr__`
> 4. `__delattr__`
> 5. `__dir__`
> 6. `__get__`
> 7. `__set__`
> 8. `__delete__`
> 9. `__set_name__`
> 10. `__slots__`
>
> Special methods that control class creation:
> 1. `__init_subclass_`
> 2. `__prepare__`
> 3. `__class__`
>
> Special methods that control instance and subclass checks:
> 1. `__instancecheck__`
> 2. `__subclasscheck__`
> 3. `__subclasshook__`
>
> Special methods that used to emulate container types:
> 1. `__iter__`
> 2. `__reversed__`
>
> Special methods that control "With" statement context managers:
> 1. `__enter__`
> 2. `__exit__`
> </details>

In general, Splice's function decorator would call the original method to perform
the desired operation first, before converting the return value to its
corresponding untrusted type. For example, to decorate `int`'s `__add__` method,
Splice converts the sum to `UntrustedInt` and returns the untrusted value.
Similarly, if a method originally returns a `str` object, Splice would convert
it to `UntrustedStr`. Additionally, if any input to the method is *synthesized*
(i.e., if an input is of untrusted type and has its synthesized attributed set),
the returned object will be synthesized as well.

This decoration approach works well in most cases, but has the following
*limitations*:
1. The type of the return value must have a corresponding untrusted class for
   Splice to convert into. Splice cannot automatically generate a new untrusted
   class from a native class. If Splice is unaware of any appropriate untrusted
   class for the return value, the original value will be returned; however,
   untrustiness will not be properly propagated afterwards.
2. This approach affects only the return value. Therefore, it is mostly designed
   for methods on *immutable* native classes. If a method affects a mutable object
   in its input (e.g., `self`), no conversion is performed.

<details>
<summary>Special Methods Related to Type Coercion</summary>
As discussed above, Splice forbids type coercion through built-in functions
such as <code>int()</code> and <code>str()</code>. This is accomplished in
<code>UntrustedMixin</code> by overriding (instead of decorating) special
methods such as <code>__int__</code>. When an object of an untrusted type
calls <code>int()</code> or <code>__int__</code>, Splice returns a
<code>TypeError</code>. Without this overriding, for example, Python would
automatically coerce an <code>UntrustedInt</code> object to <code>int</code>.
This is also the case for <code>float()</code> (<code>__float__</code>),
<code>str()</code> (<code>__str__</code>), <code>repr()</code>
(<code>__repr__</code>), <code>format()</code> (<code>__format__</code>)
and so on.
</details>

<details>
<summary>Special Methods Related to Built-in Functions with a Fixed Return Type
</summary>
Similar to type coercion methods, some special methods can override the
functionality of an operator (i.e., built-in functions) but Python forces a
particular type being returned by the operator. For example, <code>__len__</code>
can override the built-in <code>len()</code> function but Python forces the return
type to be <code>int</code>, even if elements in an iterable are untrusted. However,
unlike type coercion methods, Splice should not raise a type error for those
methods, because their corresponding functions are not type-related. The following
is the list of such functions and their corresponding special method:

1. `len()` (special method: `__len__`)
2. `hash()` (special method: `__hash__`)

Splice addresses this issue by shadowing those built-in functions so that they
directly output the decorated return value of their corresponding special method.
</details>

#### Make Regular Classes Trust-Aware
Splice uses a similar approach to make existing native classes *trust-aware*,
providing an `TrustAwareMixin` class that does most of the heavy-lifting for
creation. To create a trust-aware type, the programmer should inherit both
`TrustAwareMixin` and the corresponding native Python class. All trust-aware data
types conventionally have the prefix `TrustAware` in their class names (and use
camel case following also Python's naming convention). For example, `TrustAwareInt`
is defined as:
```python
from django.splice.utils import TrustAwareMixin
class TrustAwareInt(TrustAwareMixin, int):
    pass
```
Note that `TrustAwareMixin` must be inherited before `int`.
`TrustAwareMixin` also decorates methods in the native class. The decoration
process is similar to that of `UntrustedMixin`, except that the function
decorator itself performs a different task. Specifically, the decorator converts
any output value to its appropriate trust-aware type, unless its input contains
untrusted values. If untrusted values are involved in the operation,
`TrustAwareMixin` converts the output value to its appropriate untrusted type.

<details>
<summary>Relationships between Untrusted and Trust-Aware Classes</summary>
Any native type has a corresponding untrusted class and a trust-aware class.
Splice connects these two classes through the native type that must be inherited
by both of them. Both <code>UntrustedMixin</code> and <code>TrustAwareMixin</code>
register the untrusted and the trust-aware class with the native class so that
Splice knows how one specific untrusted-typed object can be coerced to the right
trust-aware-typed object without additional annotation. This is useful when
<code>TrustAwareMixin</code> needs to output an untrusted object or when the
programmer calls <code>to_trusted()</code> to perform a type coercion.
</details>

A python program running Splice should contain untrusted and trust-aware classes
only. Any native class in the application can stop untrustiness from being
properly propagated. The programmer can shadow native classes with their
respective trust-aware classes to effectively convert all native classes in the
program to trust-aware classes. This strategy should be used for built-in
types as well. For example, the built-in `int` type should be shadowed by
`TrustAwareInt`, so that any integer-related operation can correctly propagate
untrustiness if necessary.

Because literals of built-in types are not affected by shadowing, Splice cannot
interpose operations on literals, and this limitation can be addressed only by
modifying the built-in implementation. For example, after Splice replacing
`int` with `TrustAwareInt`:
```python
x = int(5) + 5  # x is an TrustAwareInt object because int() is controlled by Splice
y = 5 + 5       # y is a built-in int object because Splice cannot control operations on literals only
```
Additionally, any `boolean` operation must return a boolean value and is not
allowed to be interposed by Splice.

<details>
<summary>Leverage Reflected Methods for Binary Arithmetic Operations</summary>
When a literal object invokes a binary arithmetic method (e.g., <code>+</code>)
but the right operand is an object of the literal's corresponding
untrusted/trust-aware class, we can rely on the class' reflected method to
ensure untrustiness is properly handled. However, this is only possible if
operators are used and does not work if special methods are called directly.
For example,

```python
from django.splice.untrustedtypes import UntrustedInt

i = 1               # type(i) == int (built-in type)
x = int(1)          # type(x) == TrustAwareInt due to shadowing
y = UntrustedInt(1)
z = x + y           # type(z) == UntrustedInt, handled by TrustAwareInt
p = y + x           # type(p) == UntrustedInt, handled by UntrustedInt
q = i + x           # type(q) == TrustAwareInt, handled by the reflected method in TrustAwareInt
r = i + y           # type(r) == UntrustedInt, handled by the reflected method in UntrustedInt
w = i.__add__(y)    # type(w) == int, because the reflected method is not invoked
```

Note that <code>TrustAwareInt</code> and <code>UntrustedInt</code> have no
subclass relationships with each other.
</details>

#### Converting `str`
Using `str` as an example, we discuss additional considerations when converting
a native type to an untrusted and a trust-aware class. Some of these considerations
are specific to `str`, while others are more general, applicable to a wide range
of data types (e.g., all classes that are iterable).

While some built-in types such as `int` and `float` are not *iterable*, we can
iterate over each character in a `str` object, like this:
```python
s = str("A string is iterable")
for char in s:
    pass
```
A special method `__iter__`, which returns an iterator, is what makes iteration
possible. However, we cannot decorate `__iter__` the same way as other special
methods, because we do not want to convert the iterator object per se, but the
object returned by the iterator. As such, Splice overrides `__iter__` in
`UntrustedMixin` and `TrustAwareMixin`, invoking the iterator of the native class
(if defined) and converting the object returned by the iterator to its untrusted
and trust-aware type. Note that, by overriding `__iter__`, Splice modifies the
iteration behavior of *all* iterable classes, not just `str`.

Not all binary arithmetic methods have a corresponding reflected (swapped) method.
As specified in Python's data model, it is important that the emulation
(i.e., use of special methods) only be implemented to the degree that it makes
sense for the object being modeled. `str` defines the `__add__` method that
concatenates two strings to create a new string, but since concatenation is not
a *commutative* operation, `__radd__` is not implemented in the built-in type.
Consequently, Splice cannot leverage reflected methods to propagate untrustiness.
For example,
```python
from django.splice.untrustedtypes import UntrustedStr
s = "Hello " + UntrustedStr("world!")
```
Without `__radd__`, the built-in `str` object (i.e., `"Hello "`) invokes `__add__`
and creates a new built-in `str` object, `"Hello world!`. If `__radd__` were defined,
since `UntrustedStr` is a subclass of `str`, Python would invoke `__radd__` of the
the `UntrustedStr` object (because Splice would have decorated it), and the resulting
object would be of the expected `UntrustedStr` type. To achieve the same effect,
Splice defines a `__radd__` in the `UntrustedStr` and `TrustAwareStr` class. Note
that `__radd__` is *not* directly defined in `UntrustedMixin` or `TrustAwareMixin`
(which would affect all classes that subclass them) because having __radd__` may
not make sense for all classes.

<details>
<summary>Note on <code>__mul__</code> and <code>__rmul__</code> in <code>str</code></summary>
It is not always the case that a reflected method would address the type issue
like the one we discussed above. For example, we can use <code>*</code> to
concatenate the same string multiple times, like this:

```python
s = "Hello "
ss = s * 2   # ss is "Hello Hello ", and str's __mul__ was invoked
rss = 2 * s  # rss is also "Hello Hello ", but str's __rmul__ was invoked
```
In the second statement, <code>s</code> invokes the <code>mul</code> special method,
but in the third statement, <code>s</code> invokes the <code>rmul</code> method
after Python determines that <code>int</code>'s <code>mul</code> cannot handle this
type of multiplication. In both cases, if <code>s</code> is of built-in
<code>str</code> type (e.g., a string literal like in the example), Splice cannot
interpose these operations, and the return value would not be untrusted or
trusted-aware (even if the integer is untrusted or trust-aware).
</details>

# Deletion by Synthesis

## Customize a Synthesizer
Splice provides a number of built-in synthesizers (e.g., `IntSynthesizer`,
`FloatSynthesizer`, `StrSynthesizer`) that can synthesize different types of
values (e.g., `int`, `float`, and `str`). All synthesizers inherit from the base
class `Synthesizer` and output objects of their corresponding *untrusted* type
(e.g., `UntrustedInt`, `UntrustedFloat`, and `UntrustedStr`). Using these
fundamental synthesizers, the programmer can (in most cases) easily create new
synthesizers for existing Python classes. It is highly recommended that a
customized synthesizer should also inherit from `Synthesizer`. Additionally,
the new synthesizer *must* return objects of an untrusted type. This entails
creating a customized untrusted class, which can also be done easily through
inheritance. We use an example to illustrate this process.

### Create `DatetimeSynthesizer`
The following are the steps to create a synthesizer that synthesizes Python's
`datetime` objects:
1. Create a new synthesizer class `DatetimeSynthesizer` that inherits from
   `FloatSynthesizer`.
2. Define a new method in the class that converts a `datetime` object to a
   `float` object, e.g., by calling `datetime`'s `timestamp()` method.
3. Override `to_python()` in the class to convert the synthesized `float` value
   to a `datetime` object and then convert the `datetime` object to its
   corresponding untrusted type `UntrustedDatetime` (see
   [Create a New Untrusted Class](#create-a-new-untrusted-class)).
4. Override `simple_synthesis()` in the class to return an `UntrustedDatetime`
   object with its `synthesized` attribute set to `True`.

The code for `DatetimeSynthesizer` would look like this:
```python
from django.splice.synthesis import FloatSynthesizer

class DatetimeSynthesizer(FloatSynthesizer):
    @staticmethod
    def to_float(value):
        # Convert value (a datetime object) to float.
        pass

    @staticmethod
    def to_python(value):
        # Override FloatSynthesizer's to_python() to
        # convert value (a float object) back to a
        # datetime object and return an untrusted value.
        pass

    @staticmethod
    def simple_synthesis(value):
        # Override FloatSynthesizer's simple_synthesis()
        # to return an untrusted datetime object with
        # the synthesized flag set to True.
        pass
```
When a `datetime` object is to be synthesized, the programmer should call
`to_float()` first to convert the value to `float` and then use
`DatetimeSynthesizer` like a `FloatSynthesizer`. `to_python()` and
`simple_synthesis()` must return an `UntrustedDatetime` object, not Python's
`datetime` object, which requires us to define an `UntrustedDatetime` class.

### [Create a New Untrusted Class](#create-a-new-untrusted-class)
The common template to create a new untrusted class (and in this example,
the `UntrustedDatetime` class) looks like this:
```python
import datetime
from django.splice.untrustedtypes import UntrustedMixin

class UntrustedDatetime(UntrustedMixin, datetime):
    def __new__(cls, *args, synthesized=False, **kwargs):
        """We need to define __new__ because datetime is immutable!"""
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)
```
An `UntrustedDatetime` object will behave exactly like a regular `datetime` object
except that it is untrusted. All methods in `UntrustedDatetime` are inherited from
`datetime` and decorated by `UntrustedMixin`. If some methods should not output
untrusted values, the programmer should override them in `UntrustedDatetime`:
```python
import datetime
from django.splice.untrustedtypes import UntrustedMixin

class UntrustedDatetime(UntrustedMixin, datetime):
    def __new__(cls, *args, synthesized=False, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, *args, synthesized=False, **kwargs):
        super().__init__(synthesized)

    def timetuple(self):
        # We simply call datetime's timetuple() to override the
        # method so that timetuple() output will not be decorated
        return super().timetuple()
```
As mentioned before, the programmer should return an `UntrustedDatetime` object
in `DatetimeSynthesizer`'s `to_python()` and `simple_synthesis()` methods.

Note that `DatetimeSynthesizer` and `UntrustedDatetime` are implemented in
`django.splice.synthesis` and `django.splice.untrustedtypes`, respectively,
for reference.

# [Trusted Sinks](#trusted-sinks)
Trusted data sinks are locations that allow only non-synthesized data.
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
   byte string encoded from a string if necessary. The content must contain only
   trusted data.
2. `TemplateResponse`: `TemplateResponse` and its equivalent are
   what the developer typically uses to render their content dynamically.
   From Django's official documentation:
   > Unlike basic `HttpResponse` objects, `TemplateResponse` objects retain the
   > details of the template and context that was provided by the view to compute
   > the response. The final output of the response is not computed until it is
   > needed, later in the response process.

   `TemplateResponse` allows decorators or middleware to modify a response
   after it has been constructed by the view. Response context is the
   abstraction where dynamic user data is stored and therefore is where
   untrusted (and synthesized data) might leak into the trusted sink
   that is the `TemplateResponse`.

Django also defines a shortcut function `render()` that works just like
`TemplateResponse` but constructs response context and renders `HttpResponse`
directly. This is originally designed to circumvent potentially costly
middleware inspection and context modification.

Regardless of the type of responses the developer uses, Splice works with
Python's type system to check and stop illegal coercion from any untrusted data,
including synthesized data, to trusted data through `str()` (as well as other
built-in functions such as `int()` and `float()`, functions that call
`__str__` such as `print()` and `format()`, and magic methods that perform
type coercion such as `__str__`, `__format__`, `__repr__`, and `__int__`).
This means that:
1. For `HttpResponse`, the byte string input *cannot* contain untrusted data,
   since any call to construct the byte string that involves coercion to string
   is checked.
2. For both `TemplateResponse` and `render()`, right before context is rendered
   but after all decorators and middleware has run, `render_value_in_context()`
   function in `django.template.base` is called to convert any value in the
   context to a string to become part of a rendered template. During this process,
   any call to conversion is checked.

Therefore, we ensure that no untrusted data can leak out of
`Response` trusted sinks.

### Defensive Programming in Views
The developer must *explicitly* perform untrusted-to-trusted data conversion
through the `to_trusted()` method for all untrusted data types. This involves,
for example, checking if a piece of data is untrusted (since only untrusted
types define `to_trusted()`) and calling `to_trusted()` if and only if the
untrusted data is *not* synthesized.

The developer must use this defensive programming strategy on all view functions
and classes that they define.

### Views as Trusted Sinks
Unlike classic notion of trusted sinks (e.g., in a taint-tracking system where
tainted data is not allowed to flow into taint sinks) that are typically enforced
at (or right before) I/O (e.g., sockets), we enforce trusted data flow upstream
in views. We will discuss this difference in more detail in our paper.

## Trusted Data Structures
Trusted data structures are the trusted version of (untrusted) synthesizable
data structures. They store only non-synthesized data. Typically, a developer
defines a synthesizable data collection like this:
```angular2html
class MyBST(Struct):
    name = forms.CharField()
    age = forms.IntegerField()
    struct = BaseBST()
```
In this example, the underlying data structure is a (synthesizable) binary
search tree (`struct`) that stores key/value pairs in which a key (`name`) is a
string and a value (`age`) is an integer. Note that the names of those fields
are *not* keywords, so one can use any name one prefers (except `key`, which is
a keyword). This way of creating a new data structure is similar to how a new
`Model` is created in Django. `MyBST` stores untrusted data, both synthesized
and non-synthesized. For example, to insert a key/value pair to `MyBST`, you can:
```angular2html
bst = MyBST(name="Jane Doe", age=21, key="name")
bst.save()
```
`key` tells `MyBST` which field is considered the key of the key/value pair.
This way of inserting a new key/value pair is similar to how data is saved in
a Django `Model`. To access data stored in `MyBST`, you should always work on
`MyBST.objects`, which is the handle to the underlying data structure. We define
a uniform interface to manipulate the data through `objects`, so you can access
different data structures the same way. The interface is defined in
`django.splice.backends.base`.

To create a trusted version of a BST, the developer just need to add a decorator
`@trusted_struct` to the class definition:
```angular2html
@trusted_struct
class TrustedBST(Struct):
    name = forms.CharField()
    age = forms.IntegerField()
    struct = BaseBST()
```
`TrustedBST` behaves just like `MyBST` except that it stores only non-synthesized
data. The decorator decorates the `save()` method so that it checks whether data
to be inserted is synthesized or not before inserting only non-synthesized data.

### Defensive Programming in Data Structures
The developer should practice *defensive programming* when retrieving and
manipulating data stored in a synthesizable data structure. For example, when
using data obtained from `MyBST` (the example above), *always* check whether
the data is synthesized:
```angular2html
data = MyBST.objects.get("Jane Doe")
if not data.synthesized:  # Defensive programming
    # Do something useful here.
```
Similarly, the developer must ensure data to be inserted to a trusted data
structure (e.g., `TrustedBST` in the example above) is not synthesized before
calling `save()`.

# [Notes](#notes)
* The following built-in functions work as intended or need not be handled:
    * `abs()`: untrusted input returns untrusted output
      (e.g., `UntrustedFloat` -> `UntrustedFloat`).
    * `breakpoint()`: for debugging; no special handling is needed.
    * `callable()`: test whether input appears callable. Since only non-callable
      data can be synthesized, this built-in function should always return `False`
      for trusted and untrusted data anyways.
    * `delattr()`: delete the named attribute; no special handling is needed.
    * `dict()`: we need only elements in the `dict` to be untrusted, so no special
      handling is needed on the `dict` object itself.
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

* Analogous to control-flow-based under-tainting, there exist issues related
  to *control-flow-based trust propagation*. For example:
  ```angular2html
  x = UntrustedStr("x")
  x_length = len(x)  # returns an UntrustedInt object
  if x_length < 3:
      y = 3          # y is a trusted int object
  else:
      y = x_length   # y is an UntrustedInt object
  ```
  In the example above, ideally `y` should always be an `UntrustedInt` object
  regardless of the condition since the condition itself (`x_length < 3`) uses
  an untrusted value (`x_length`) for comparison and therefore it should not be
  trusted. However, because we cannot handle control-flow trust propagation,
  `y` can be made trusted. The same issue also exists in list indexing:
  ```angular2html
  x = UntrustedInt(3)
  y = [1, 2, 3, 4, 5]
  z = y[x]            # z is a trusted int object
  ```
  In this example, ideally `z` should be an `UntrustedInt` object because it is
  the result of an *untrusted slice* of a trusted list. *Note that this particular
  issue can be addressed by overriding `__getitem__()` of `list`.*

* The `bool` type cannot be subclassed (unlike `int` or `float`, for example).
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
  other hand, we suspect that failure to having an `UntrustedBool` type may cause
  problems only if `bool` values are used "unorthodoxly", for example:
  ```angular2html
  x = UntrustedInt(5)
  y = bool(x)         # y unfortunately is a trusted bool object
  z = bool(x) + 1     # Now z is a trusted int object
  ```
  However, using a boolean value as an integer is not a common practice. More
  likely, you would use a boolean value to manipulate control flow (or less
  frequently as a 0/1 index), but then the issue is not really about `bool`
  but about control-flow-based trust propagation.

# To-Do's:
* [x] `complex()` (`__complex__`): we cannot yet handle `complex` built-in type.
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
    * `hash()`: while `__hash__()` returns an `UntrustedInt` object, `hash()`
      always returns an integer.
    * `hex()`: always return a string.
    * `oct()`: always return a string.
    * `ord()`: take only a string as input (but not `UntrustedStr`) and return
      a string.

* [ ] Some built-in types are not (yet) handled by Splice.
    * [ ] `bytearray`: :construction: we are encountering issues with `bytearray`
      (see comments in untrustedtypes.py).
    * [ ] `bytes`
    * [x] `bool`: cannot be handled by subclassing (see [Notes](#notes)).
    * [ ] `complex`

* [ ] Some built-in functions are not yet handled by Splice.
    * `compile()`
    * `range()`

* [ ] Go through magic methods and identify ones that should not be
  decorated by `add_synthesis_to_func()` in `untrustedtypes.py`.

* [x] Note in the paper that unlike classic notion of trusted sinks that are
  typically enforced at I/O (sockets), we perform this enforcement upstream
  in `Response`. This could be an interesting discussion point!

* [x] If `HttpRespone` can be enforced by the type system (through `str()`
  or `format()`) why can't we do the same with `TemplateResponse` (or `render()`)?

* [x] Check if decorators change the methods in the base classes that caused
  the `isinstance([], UserString) == True` problem.

* [ ] Should `hash()` return an untrusted value?

* [ ] What is the reasonable policy of untrusted data types in a program? For
  example, how do we want to handle control flow when a condition is untrusted
  (e.g., a Draconian policy might be that conditions used in a control flow
  cannot contain untrusted values)? This could be an interesting discussion point
  in the paper, especially that we can tie this with the `bool` issue that
  we encountered, which is typically used for conditions.

* [ ] Can we adapt an in-memory SQL database in Python to Django and our
  framework? Look into a less contrived but still simple Django application and
  see what schemas and queries it use and how easy it is that we can handle
  them with synthesis? For example, perhaps we can convert Django form fields'
  constraints (which are used for validation) into synthesis constraints that
  can be used to synthesize new values? If so, this would be a perfect mechanism
  to incorporate synthesis to databases without additional developer burden.
