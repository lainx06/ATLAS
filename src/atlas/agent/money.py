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


def price_problem(value) -> str | None:
    """Why `value` is not a supported price, or None."""
    if not isinstance(value, Decimal):
        return "must be a Decimal"
    if not value.is_finite():
        return "must be finite"
    sign, _, exponent = value.as_tuple()
    if sign:  # negative, or a negative zero (which would print as -0)
        return "must be non-negative"
    if exponent < -PRICE_DECIMALS:
        return f"must have at most {PRICE_DECIMALS} decimal places"
    with exact():
        if value > MAX_PRICE:
            return "must be at most 1e100 USD per token"
    return None


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
