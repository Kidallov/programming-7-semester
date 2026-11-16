"""Самодостаточные значения и состояния предметной модели."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from .errors import CurrencyMismatchError, InvalidValueError
from .identifiers import ImmutableValue, nonempty_text, require_type


class Sku(ImmutableValue):
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", nonempty_text(value))

    def value(self) -> str:
        return self._value

    def _parts(self) -> tuple:
        return (self._value,)


class Currency(ImmutableValue):
    __slots__ = ("_code",)

    def __init__(self, code: str) -> None:
        code = nonempty_text(code)
        if len(code) != 3 or not code.isascii() or not code.isalpha():
            raise InvalidValueError("Код валюты — три латинские буквы.")
        object.__setattr__(self, "_code", code.upper())

    def code(self) -> str:
        return self._code

    def _parts(self) -> tuple:
        return (self._code,)


class Quantity(ImmutableValue):
    __slots__ = ("_value",)

    def __init__(self, value: int) -> None:
        if type(value) is not int or value <= 0:
            raise InvalidValueError("Количество — положительное целое число.")
        object.__setattr__(self, "_value", value)

    def value(self) -> int:
        return self._value

    def _parts(self) -> tuple:
        return (self._value,)


class Money(ImmutableValue):
    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Decimal, currency: Currency) -> None:
        require_type(currency, Currency)
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0:
            raise InvalidValueError("Сумма — конечный неотрицательный Decimal.")
        object.__setattr__(self, "_amount", amount)
        object.__setattr__(self, "_currency", currency)

    def amount(self) -> Decimal:
        return self._amount

    def currency(self) -> Currency:
        return self._currency

    def add(self, other: "Money") -> "Money":
        require_type(other, Money)
        if self._currency != other._currency:
            raise CurrencyMismatchError("Нельзя складывать разные валюты.")
        return Money(self._amount + other._amount, self._currency)

    def multiply(self, quantity: Quantity) -> "Money":
        require_type(quantity, Quantity)
        return Money(self._amount * quantity.value(), self._currency)

    def _parts(self) -> tuple:
        return (self._amount, self._currency)

    def __str__(self) -> str:
        return f"{self._amount:.2f} {self._currency.code()}"


class ShippingAddress(ImmutableValue):
    __slots__ = ("_city", "_street", "_building", "_postal_code")

    def __init__(self, city: str, street: str, building: str, postal_code: str) -> None:
        parts = tuple(nonempty_text(x) for x in (city, street, building, postal_code))
        object.__setattr__(self, "_city", parts[0])
        object.__setattr__(self, "_street", parts[1])
        object.__setattr__(self, "_building", parts[2])
        object.__setattr__(self, "_postal_code", parts[3])

    def city(self) -> str:
        return self._city

    def street(self) -> str:
        return self._street

    def building(self) -> str:
        return self._building

    def postal_code(self) -> str:
        return self._postal_code

    def _parts(self) -> tuple:
        return (self._city, self._street, self._building, self._postal_code)


class OrderStatus(Enum):
    DRAFT = "DRAFT"
    PLACED = "PLACED"
    CANCELLED = "CANCELLED"


class LineKind(Enum):
    PAID = "PAID"
    GIFT = "GIFT"


class StockBalance(ImmutableValue):
    __slots__ = ("_value",)

    def __init__(self, value: int) -> None:
        if type(value) is not int or value < 0:
            raise InvalidValueError("Остаток — неотрицательное целое число.")
        object.__setattr__(self, "_value", value)

    def value(self) -> int:
        return self._value

    def increase(self, quantity: Quantity) -> "StockBalance":
        require_type(quantity, Quantity)
        return StockBalance(self._value + quantity.value())

    def decrease(self, quantity: Quantity) -> "StockBalance":
        require_type(quantity, Quantity)
        return StockBalance(self._value - quantity.value())

    def _parts(self) -> tuple:
        return (self._value,)


class ReservationStatus(Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class ReservationDeadline(ImmutableValue):
    """Сохранённый момент срока; часы ОС не читаются."""

    __slots__ = ("_moment",)

    def __init__(self, moment: datetime) -> None:
        require_aware_datetime(moment)
        object.__setattr__(self, "_moment", moment)

    def is_due(self, now: datetime) -> bool:
        require_aware_datetime(now)
        return self._moment <= now

    def moment(self) -> datetime:
        return self._moment

    def _parts(self) -> tuple:
        return (self._moment,)


def require_aware_datetime(moment: datetime) -> None:
    if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
        raise InvalidValueError("Требуется datetime с часовым поясом.")
