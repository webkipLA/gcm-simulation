"""Pluggable arithmetic backends for the FORTRAN model.

Why this exists
---------------
The FORTRAN program compares energies with ``.GE.`` / ``.GT.``, and in the paper's parameter
space *exact ties* are common (e.g. three light-load problems require 3 × 1.1 = 3.3, and ten
equal-energy decision makers supply 10 × 0.6 × 0.55 = 3.3 in one period). Which side of a tie
the program lands on therefore depends on the floating-point arithmetic of the machine that ran
it, in 1972 an IBM System/360 with 24-bit *hexadecimal* single precision and truncating
arithmetic. Three backends are provided:

``ExactArithmetic`` (default)
    IEEE double precision, but comparisons are made after rounding both operands to
    ``precision`` decimal places. Because every quantity in the model is a short decimal
    fraction, this realises the paper's stated semantics ("equals *or exceeds*") exactly.
``Float64Arithmetic``
    Plain IEEE double precision, comparisons as-is. Ties are then decided by binary rounding
    noise, which is *not* what the original machine did.
``Ibm360Arithmetic``
    Emulation of System/360 short hexadecimal floating point: values are ±0.h₁…h₆ × 16ᵉ with a
    24-bit fraction; every add, subtract, multiply and divide truncates the exact result toward
    zero after normalisation (the post-1967 "guard digit" behaviour is approximated by truncating
    the exact result). Decimal constants are converted either by truncation or to nearest.
"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from typing import Any, Protocol, runtime_checkable

Number = Any  # float or HexFloat


@runtime_checkable
class Arithmetic(Protocol):
    """A number system: constants, zero, and the two comparisons the program performs."""

    name: str

    def const(self, x: float | str) -> Number:
        """Convert a decimal constant / integer to a number of this backend."""
        ...

    def zero(self) -> Number: ...

    def ge(self, a: Number, b: Number) -> bool:
        """``a .GE. b`` (used in the allocation loops: skip candidate if deficit >= best)."""
        ...

    def gt(self, a: Number, b: Number) -> bool:
        """``a .GT. b`` (used in the decision test: choice not made if XERC > XEE)."""
        ...

    def to_float(self, a: Number) -> float: ...


# ---------------------------------------------------------------------------------------------
class ExactArithmetic:
    """Double precision with decimal-quantised comparisons (exact for this model's inputs)."""

    def __init__(self, precision: int = 9) -> None:
        self.precision = precision
        self.name = f"exact(p={precision})"

    def const(self, x):
        return float(x)

    def zero(self):
        return 0.0

    def ge(self, a, b):
        return round(a, self.precision) >= round(b, self.precision)

    def gt(self, a, b):
        return round(a, self.precision) > round(b, self.precision)

    def to_float(self, a):
        return float(a)


class Float64Arithmetic:
    """Plain IEEE double precision; comparisons subject to binary rounding noise."""

    name = "float64"

    def const(self, x):
        return float(x)

    def zero(self):
        return 0.0

    def ge(self, a, b):
        return a >= b

    def gt(self, a, b):
        return a > b

    def to_float(self, a):
        return float(a)


# ---------------------------------------------------------------------------------------------
_FRACTION_BITS = 24


@lru_cache(maxsize=1 << 16)
def _truncate_hex(x: Fraction) -> Fraction:
    """Truncate a rational toward zero to a normalised 24-bit base-16 fraction."""
    if x == 0:
        return x
    neg = x < 0
    a = -x if neg else x
    e = 0
    if a >= 1:
        while a >= Fraction(16) ** e:
            e += 1
    else:
        while a < Fraction(16) ** (e - 1):
            e -= 1
    # now 16^(e-1) <= a < 16^e  ⇒ a / 16^e ∈ [1/16, 1): normalised fraction
    scale = Fraction(2**_FRACTION_BITS) / Fraction(16) ** e
    scaled = a * scale
    m = scaled.numerator // scaled.denominator
    r = Fraction(m) / scale
    return -r if neg else r


@lru_cache(maxsize=1 << 16)
def _nearest_hex(x: Fraction) -> Fraction:
    """Round a rational to the nearest normalised 24-bit base-16 fraction (ties away from 0)."""
    if x == 0:
        return x
    neg = x < 0
    a = -x if neg else x
    e = 0
    if a >= 1:
        while a >= Fraction(16) ** e:
            e += 1
    else:
        while a < Fraction(16) ** (e - 1):
            e -= 1
    scale = Fraction(2**_FRACTION_BITS) / Fraction(16) ** e
    scaled = a * scale + Fraction(1, 2)
    m = scaled.numerator // scaled.denominator
    r = Fraction(m) / scale
    return -r if neg else r


class HexFloat:
    """A System/360 short-precision hexadecimal floating-point value."""

    __slots__ = ("v",)

    def __init__(self, v: Fraction, exact: bool = False) -> None:
        self.v = v if exact else _truncate_hex(v)

    @staticmethod
    def _coerce(o: HexFloat | float | Fraction) -> Fraction:
        if isinstance(o, HexFloat):
            return o.v
        if isinstance(o, int):
            return Fraction(o)
        if isinstance(o, Fraction):
            return o
        return _truncate_hex(Fraction(repr(float(o))))

    def __add__(self, o):
        return HexFloat(self.v + self._coerce(o))

    __radd__ = __add__

    def __sub__(self, o):
        return HexFloat(self.v - self._coerce(o))

    def __rsub__(self, o):
        return HexFloat(self._coerce(o) - self.v)

    def __mul__(self, o):
        return HexFloat(self.v * self._coerce(o))

    __rmul__ = __mul__

    def __truediv__(self, o):
        return HexFloat(self.v / self._coerce(o))

    def __neg__(self):
        return HexFloat(-self.v, exact=True)

    def __lt__(self, o):
        return self.v < self._coerce(o)

    def __le__(self, o):
        return self.v <= self._coerce(o)

    def __gt__(self, o):
        return self.v > self._coerce(o)

    def __ge__(self, o):
        return self.v >= self._coerce(o)

    def __eq__(self, o):
        return self.v == self._coerce(o)

    def __hash__(self):
        return hash(self.v)

    def __float__(self):
        return float(self.v)

    def __repr__(self):
        return f"HexFloat({float(self.v)!r})"


class Ibm360Arithmetic:
    """Emulated IBM System/360 short hexadecimal floating point (see module docstring)."""

    def __init__(self, constant_conversion: str = "truncate") -> None:
        if constant_conversion not in ("truncate", "nearest"):
            raise ValueError("constant_conversion must be 'truncate' or 'nearest'")
        self.constant_conversion = constant_conversion
        self.name = f"ibm360({constant_conversion})"

    def const(self, x):
        if isinstance(x, HexFloat):
            return x
        if isinstance(x, int):
            return HexFloat(Fraction(x))  # integers up to 2^24 are exact
        frac = Fraction(str(x)) if isinstance(x, str) else Fraction(repr(float(x)))
        conv = _truncate_hex if self.constant_conversion == "truncate" else _nearest_hex
        return HexFloat(conv(frac), exact=True)

    def zero(self):
        return HexFloat(Fraction(0), exact=True)

    def ge(self, a, b):
        return a >= b

    def gt(self, a, b):
        return a > b

    def to_float(self, a):
        return float(a)


def get_arithmetic(name: str | Arithmetic) -> Arithmetic:
    """Resolve a backend by name: ``"exact"``, ``"float64"``, ``"ibm360"``, ``"ibm360-nearest"``."""
    if not isinstance(name, str):
        return name
    if name == "exact":
        return ExactArithmetic()
    if name == "float64":
        return Float64Arithmetic()
    if name == "ibm360":
        return Ibm360Arithmetic("truncate")
    if name == "ibm360-nearest":
        return Ibm360Arithmetic("nearest")
    raise ValueError(f"unknown arithmetic backend {name!r}")
