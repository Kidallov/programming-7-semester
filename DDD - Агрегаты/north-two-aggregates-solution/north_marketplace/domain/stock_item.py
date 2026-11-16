"""Складская позиция — один товар на одном складе."""

from datetime import datetime

from .errors import (
    DuplicateReservationError, InsufficientStockError,
    ReservationNotFoundError, ReservationStateError,
)
from .identifiers import (
    ImmutableValue, OrderId, ReservationId, StockItemId, WarehouseId, require_type,
)
from .values import (
    Quantity, ReservationDeadline, ReservationStatus, Sku, StockBalance, require_aware_datetime,
)


class StockItem:
    __slots__ = ("_id", "_warehouse_id", "_sku", "_physical_balance", "_reservations")

    def __init__(self, stock_item_id: StockItemId, warehouse_id: WarehouseId,
                 sku: Sku, physical_balance: StockBalance) -> None:
        require_type(stock_item_id, StockItemId)
        require_type(warehouse_id, WarehouseId)
        require_type(sku, Sku)
        require_type(physical_balance, StockBalance)
        self._id = stock_item_id
        self._warehouse_id = warehouse_id
        self._sku = sku
        self._physical_balance = physical_balance
        self._reservations: list[StockReservation] = []

    def id(self) -> StockItemId:
        return self._id

    def warehouse_id(self) -> WarehouseId:
        return self._warehouse_id

    def sku(self) -> Sku:
        return self._sku

    def physical_balance(self) -> StockBalance:
        return self._physical_balance

    def active_reserved_quantity(self) -> StockBalance:
        return StockBalance(sum(r._snapshot().quantity().value() for r in self._reservations
                                if r._snapshot().status() is ReservationStatus.ACTIVE))

    def available_quantity(self) -> StockBalance:
        return StockBalance(self._physical_balance.value() - self.active_reserved_quantity().value())

    def reservations(self) -> tuple["ReservationSummary", ...]:
        return tuple(reservation._snapshot() for reservation in self._reservations)

    def reserve(self, reservation_id: ReservationId, order_id: OrderId,
                quantity: Quantity, deadline: ReservationDeadline) -> None:
        require_type(reservation_id, ReservationId)
        require_type(order_id, OrderId)
        require_type(quantity, Quantity)
        require_type(deadline, ReservationDeadline)
        if any(r.id() == reservation_id for r in self._reservations):
            raise DuplicateReservationError("Идентификатор резерва уже используется.")
        if quantity.value() > self.available_quantity().value():
            raise InsufficientStockError("Недостаточно доступного остатка для резерва.")
        self._reservations.append(StockReservation(reservation_id, order_id, quantity, deadline))

    def release_reservation(self, reservation_id: ReservationId) -> None:
        require_type(reservation_id, ReservationId)
        for reservation in self._reservations:
            if reservation.id() == reservation_id:
                reservation._release()
                return
        raise ReservationNotFoundError("Резерв не найден.")

    def expire_reservations(self, now: datetime) -> int:
        # Проверяем время до первого перехода, чтобы отказ не менял часть резервов.
        require_aware_datetime(now)
        return sum(reservation._expire_if_due(now) for reservation in self._reservations)

    def receive(self, quantity: Quantity) -> None:
        require_type(quantity, Quantity)
        self._physical_balance = self._physical_balance.increase(quantity)

    def write_off(self, quantity: Quantity) -> None:
        require_type(quantity, Quantity)
        if quantity.value() > self.available_quantity().value():
            raise InsufficientStockError("Недостаточно доступного остатка для списания.")
        self._physical_balance = self._physical_balance.decrease(quantity)


class ReservationSummary(ImmutableValue):
    """Неизменяемое представление резерва для чтения."""

    __slots__ = ("_reservation_id", "_order_id", "_quantity", "_deadline", "_status")

    def __init__(self, reservation_id: ReservationId, order_id: OrderId,
                 quantity: Quantity, deadline: ReservationDeadline, status: ReservationStatus) -> None:
        require_type(reservation_id, ReservationId)
        require_type(order_id, OrderId)
        require_type(quantity, Quantity)
        require_type(deadline, ReservationDeadline)
        require_type(status, ReservationStatus)
        object.__setattr__(self, "_reservation_id", reservation_id)
        object.__setattr__(self, "_order_id", order_id)
        object.__setattr__(self, "_quantity", quantity)
        object.__setattr__(self, "_deadline", deadline)
        object.__setattr__(self, "_status", status)

    def reservation_id(self) -> ReservationId:
        return self._reservation_id

    def order_id(self) -> OrderId:
        return self._order_id

    def quantity(self) -> Quantity:
        return self._quantity

    def deadline(self) -> ReservationDeadline:
        return self._deadline

    def status(self) -> ReservationStatus:
        return self._status

    def _parts(self) -> tuple:
        return (self._reservation_id, self._order_id, self._quantity, self._deadline, self._status)


class StockReservation:
    """Внутренняя сущность. Команды изменения вызывает только StockItem."""

    __slots__ = ("_data",)

    def __init__(self, reservation_id: ReservationId, order_id: OrderId,
                 quantity: Quantity, deadline: ReservationDeadline) -> None:
        self._data = ReservationSummary(reservation_id, order_id, quantity, deadline,
                                        ReservationStatus.ACTIVE)

    def id(self) -> ReservationId:
        return self._data.reservation_id()

    def _snapshot(self) -> ReservationSummary:
        return self._data

    def _release(self) -> None:
        if self._data.status() is not ReservationStatus.ACTIVE:
            raise ReservationStateError("Освободить можно только активный резерв.")
        self._set_status(ReservationStatus.RELEASED)

    def _expire_if_due(self, now: datetime) -> bool:
        if self._data.status() is ReservationStatus.ACTIVE and self._data.deadline().is_due(now):
            self._set_status(ReservationStatus.EXPIRED)
            return True
        return False

    def _set_status(self, status: ReservationStatus) -> None:
        d = self._data
        self._data = ReservationSummary(d.reservation_id(), d.order_id(), d.quantity(), d.deadline(), status)
