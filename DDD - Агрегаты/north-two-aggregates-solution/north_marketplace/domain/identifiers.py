"""Неизменяемые идентификаторы: тип входит в равенство и хеш."""

from .errors import InvalidValueError


class ImmutableValue:
    """Примесь неизменяемости. Конкретные значения определяют _parts()."""

    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Объект-значение неизменяем.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Объект-значение неизменяем.")

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self._parts() == other._parts()

    def __hash__(self) -> int:
        return hash((type(self), self._parts()))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(repr(x) for x in self._parts())})"


def require_type(value: object, expected: type) -> None:
    if not isinstance(value, expected):
        raise InvalidValueError(f"Ожидается {expected.__name__}.")


def nonempty_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidValueError("Ожидается непустая строка.")
    return value.strip()


class Identifier(ImmutableValue):
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", nonempty_text(value))

    def value(self) -> str:
        return self._value

    def _parts(self) -> tuple:
        return (self._value,)


class OrderId(Identifier):
    __slots__ = ()


class OrderLineId(Identifier):
    __slots__ = ()


class BuyerId(Identifier):
    __slots__ = ()


class SellerId(Identifier):
    __slots__ = ()


class StockItemId(Identifier):
    __slots__ = ()


class WarehouseId(Identifier):
    __slots__ = ()


class ReservationId(Identifier):
    __slots__ = ()
