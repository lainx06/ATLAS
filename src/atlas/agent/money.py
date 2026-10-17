"""Exact money arithmetic for cost accounting (T-06 slice 3 repair pass 2).

Every monetary computation (prices x token counts, sums, comparisons, text) runs inside
`exact()`, a private `decimal` context. It never uses the caller's ambient context, so
precision, rounding and trap settings elsewhere cannot change a result.

**Supported range (checked before use, so results are always exact and finite):**

- token counts, configured or reported: integers from 0 to `MAX_TOKEN_COUNT` (10**100);
- prices: finite, non-negative `Decimal` values of at most `MAX_PRICE` (10**100 USD per token)
  with at most `PRICE_DECIMALS` (30) decimal places.

Within that range a cost has at most 231 significant digits, and a run sums at most a few
dozen of them, so the private context's 400-digit precision represents every result exactly.
Rounding is trapped (`Inexact`, `Rounded`) as well as overflow and invalid operations: if an
amount could ever not be represented exactly, the computation raises `MoneyError` instead of
returning a rounded or non-finite figure. Configurations outside the range are rejected before
any client exists; reported counts outside it are invalid usage.
"""

import decimal
from contextlib import contextmanager
from decimal import Decimal

from atlas.agent.client import MAX_TOKEN_COUNT

MAX_PRICE = Decimal("1e100")  # USD per token
PRICE_DECIMALS = 30
_CONTEXT = decimal.Context(
    prec=400,
    rounding=decimal.ROUND_HALF_EVEN,
    Emax=999,
    Emin=-999,
    capitals=1,
    clamp=0,
    flags=[],
    traps=[
        decimal.InvalidOperation,
        decimal.DivisionByZero,
        decimal.Overflow,
        decimal.Underflow,
        decimal.Inexact,
        decimal.Rounded,
        decimal.Clamped,
    ],
)


class MoneyError(ValueError):
    """An amount that cannot be represented exactly (never a rounded or infinite figure)."""


@contextmanager
def exact():
    """Run money arithmetic in the private exact context; any decimal signal becomes
    MoneyError."""
    try:
        with decimal.localcontext(_CONTEXT.copy()):
            yield
    except decimal.DecimalException:
        raise MoneyError("amount not exactly representable") from None


MAX_EXPONENT = 100  # MAX_PRICE is 10**MAX_EXPONENT


def _decimal_problem(value, unit: str) -> str | None:
    """Why `value` is outside the supported range, decided from its tuple alone: no
    arithmetic, comparison or formatting, so a short input such as "1E+100000" is rejected
    without ever being expanded."""
    if not isinstance(value, Decimal):
        return "must be a Decimal"
    if not value.is_finite():
        return "must be finite"
    sign, digits, exponent = value.as_tuple()
    if sign:  # negative, or a negative zero (which would print as -0)
        return "must be non-negative"
    if exponent < -PRICE_DECIMALS:
        return f"must have at most {PRICE_DECIMALS} decimal places"
    # The value is d0.d1d2... x 10**adjusted (d0 >= 1 unless the value is zero).
    adjusted = len(digits) - 1 + exponent
    if adjusted > MAX_EXPONENT or (
        adjusted == MAX_EXPONENT and (digits[0] > 1 or any(digits[1:]))
    ):
        return f"must be at most 1e100 {unit}"
    return None


def price_problem(value) -> str | None:
    """Why `value` is not a supported price, or None."""
    return _decimal_problem(value, "USD per token")


def amount_problem(value) -> str | None:
    """Why `value` is not a supported USD amount (a spending limit), or None. Same range as a
    price: finite, non-negative, at most 1e100 and at most 30 decimal places."""
    return _decimal_problem(value, "USD")


def exceeds(a: Decimal, b: Decimal) -> bool:
    """a > b, compared exactly."""
    with exact():
        return a > b


def times(count: int, amount: Decimal) -> Decimal:
    """`count` x a USD amount (for example attempts x a per-request bound), exactly."""
    if type(count) is not int or not 0 <= count <= MAX_TOKEN_COUNT:
        raise MoneyError("count outside the supported range")
    with exact():
        return Decimal(count) * amount


def cost(tokens: int, price: Decimal) -> Decimal:
    """`tokens` x `price`, exactly."""
    if type(tokens) is not int or not 0 <= tokens <= MAX_TOKEN_COUNT:
        raise MoneyError("token count outside the supported range")
    if price_problem(price) is not None:
        raise MoneyError("price outside the supported range")
    with exact():
        return Decimal(tokens) * price


def total(amounts) -> Decimal:
    """The exact sum of finite amounts."""
    with exact():
        result = Decimal(0)
        for amount in amounts:
            if not isinstance(amount, Decimal) or not amount.is_finite():
                raise MoneyError("amount is not a finite Decimal")
            result += amount
        return result


def difference(a: Decimal, b: Decimal) -> Decimal:
    with exact():
        return a - b


def text(amount: Decimal) -> str:
    """Fixed-point text, never exponent notation such as 0E-7."""
    with exact():
        return format(amount, "f")
