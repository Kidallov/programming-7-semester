"""Предметные причины отказа. Ошибочная команда не меняет агрегат."""


class DomainError(Exception):
    """Базовая ошибка предметной модели."""


class InvalidValueError(DomainError):
    """Некорректное значение или тип аргумента."""


class OrderStateError(DomainError):
    """Команда недоступна в текущем состоянии заказа."""


class IncompleteOrderError(DomainError):
    """Заказ не готов к размещению."""


class CurrencyMismatchError(DomainError):
    """Валюты не совпадают."""


class SellerMismatchError(DomainError):
    """Строка принадлежит другому продавцу."""


class DuplicateOrderLineError(DomainError):
    """Идентификатор строки уже занят."""


class OrderLineNotFoundError(DomainError):
    """Строка не найдена в заказе."""


class InsufficientStockError(DomainError):
    """Недостаточно свободного остатка."""


class ReservationError(DomainError):
    """Базовая ошибка операции с резервом."""


class DuplicateReservationError(ReservationError):
    """Идентификатор резерва уже занят."""


class ReservationNotFoundError(ReservationError):
    """Резерв не найден."""


class ReservationStateError(ReservationError):
    """Переход из текущего состояния резерва запрещён."""
