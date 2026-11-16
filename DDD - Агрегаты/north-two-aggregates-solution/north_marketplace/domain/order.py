"""Заказ защищает состав, снимок цены и жизненный цикл."""

from decimal import Decimal

from .errors import (
    CurrencyMismatchError, DuplicateOrderLineError, IncompleteOrderError, InvalidValueError,
    OrderLineNotFoundError, OrderStateError, SellerMismatchError,
)
from .identifiers import BuyerId, ImmutableValue, OrderId, OrderLineId, SellerId, nonempty_text, require_type
from .values import Currency, LineKind, Money, OrderStatus, Quantity, ShippingAddress, Sku


class OrderLineSnapshot(ImmutableValue):
    __slots__ = ("_id", "_sku", "_title", "_unit_price", "_quantity", "_seller_id", "_kind")

    def __init__(self, line_id: OrderLineId, sku: Sku, title: str,
                 seller_id: SellerId, unit_price: Money, quantity: Quantity, kind: LineKind) -> None:
        require_type(seller_id, SellerId)
        require_type(line_id, OrderLineId)
        require_type(sku, Sku)
        require_type(unit_price, Money)
        require_type(quantity, Quantity)
        require_type(kind, LineKind)
        if kind is LineKind.PAID and unit_price.amount() <= 0:
            raise InvalidValueError("Платная строка требует положительную цену.")
        if kind is LineKind.GIFT and unit_price.amount() != 0:
            raise InvalidValueError("Цена подарка должна быть нулевой.")
        title = nonempty_text(title)
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_seller_id", seller_id)
        object.__setattr__(self, "_id", line_id)
        object.__setattr__(self, "_sku", sku)
        object.__setattr__(self, "_title", title)
        object.__setattr__(self, "_unit_price", unit_price)
        object.__setattr__(self, "_quantity", quantity)

    def id(self) -> OrderLineId:
        return self._id

    def kind(self) -> LineKind:
        return self._kind

    def seller_id(self) -> SellerId:
        return self._seller_id

    def sku(self) -> Sku:
        return self._sku

    def title(self) -> str:
        return self._title

    def unit_price(self) -> Money:
        return self._unit_price

    def quantity(self) -> Quantity:
        return self._quantity

    def subtotal(self) -> Money:
        return self._unit_price.multiply(self._quantity)

    def _parts(self) -> tuple:
        return (self._id, self._sku, self._title, self._unit_price, self._quantity, self._seller_id, self._kind)


class OrderLine:
    """Внутренняя сущность: изменение количества доступно только корню."""

    __slots__ = ("_data",)

    def __init__(self, line_id: OrderLineId, sku: Sku, title: str,
                 seller_id: SellerId, unit_price: Money, quantity: Quantity, kind: LineKind) -> None:
        self._data = OrderLineSnapshot(line_id, sku, title, seller_id, unit_price, quantity, kind)

    def id(self) -> OrderLineId:
        return self._data.id()

    def subtotal(self) -> Money:
        return self._data.subtotal()

    def _change_quantity(self, quantity: Quantity) -> None:
        d = self._data
        self._data = OrderLineSnapshot(d.id(), d.sku(), d.title(), d.seller_id(), d.unit_price(), quantity, d.kind())

    def _snapshot(self) -> OrderLineSnapshot:
        return self._data


class Order:
    __slots__ = ("_id", "_buyer_id", "_currency", "_status", "_lines", "_shipping_address", "_seller_id")

    def __init__(self, order_id: OrderId, buyer_id: BuyerId, currency: Currency) -> None:
        require_type(order_id, OrderId)
        require_type(buyer_id, BuyerId)
        require_type(currency, Currency)
        self._id = order_id
        self._buyer_id = buyer_id
        self._currency = currency
        self._status = OrderStatus.DRAFT
        self._seller_id: SellerId | None = None
        self._lines: list[OrderLine] = []
        self._shipping_address: ShippingAddress | None = None

    def id(self) -> OrderId:
        return self._id

    def buyer_id(self) -> BuyerId:
        return self._buyer_id

    def currency(self) -> Currency:
        return self._currency

    def status(self) -> OrderStatus:
        return self._status

    def seller_id(self) -> SellerId | None:
        return self._seller_id

    def lines(self) -> tuple[OrderLineSnapshot, ...]:
        return tuple(line._snapshot() for line in self._lines)

    def shipping_address(self) -> ShippingAddress | None:
        return self._shipping_address

    def total(self) -> Money:
        result = Money(Decimal("0"), self._currency)
        for line in self._lines:
            result = result.add(line.subtotal())
        return result

    def _require_draft(self) -> None:
        if self._status is not OrderStatus.DRAFT:
            raise OrderStateError("Изменять и размещать можно только черновик.")

    def add_paid_line(self, line_id: OrderLineId, sku: Sku, title: str,
                      seller_id: SellerId, price: Money, quantity: Quantity) -> None:
        self._add_line(line_id, sku, title, seller_id, price, quantity, LineKind.PAID)

    def add_gift_line(self, line_id: OrderLineId, sku: Sku, title: str,
                      seller_id: SellerId, quantity: Quantity) -> None:
        self._add_line(line_id, sku, title, seller_id,
                       Money(Decimal("0"), self._currency), quantity, LineKind.GIFT)

    def _add_line(self, line_id: OrderLineId, sku: Sku, title: str,
                 seller_id: SellerId, unit_price: Money, quantity: Quantity, kind: LineKind) -> None:
        self._require_draft()
        line = OrderLine(line_id, sku, title, seller_id, unit_price, quantity, kind)
        if any(existing.id() == line_id for existing in self._lines):
            raise DuplicateOrderLineError("Идентификатор строки уже используется.")
        if unit_price.currency() != self._currency:
            raise CurrencyMismatchError("Валюта строки не совпадает с валютой заказа.")
        if self._seller_id is not None and seller_id != self._seller_id:
            raise SellerMismatchError("Все строки должны принадлежать одному продавцу.")
        self._lines.append(line)
        self._seller_id = seller_id

    def change_line_quantity(self, line_id: OrderLineId, quantity: Quantity) -> None:
        self._require_draft()
        require_type(line_id, OrderLineId)
        require_type(quantity, Quantity)
        for line in self._lines:
            if line.id() == line_id:
                line._change_quantity(quantity)
                return
        raise OrderLineNotFoundError("Строка не найдена.")

    def set_shipping_address(self, address: ShippingAddress) -> None:
        self._require_draft()
        require_type(address, ShippingAddress)
        self._shipping_address = address

    def place(self) -> None:
        self._require_draft()
        if (not self._lines or self._shipping_address is None
                or not any(line._snapshot().kind() is LineKind.PAID for line in self._lines)
                or self.total().amount() <= 0):
            raise IncompleteOrderError("Для размещения нужны строки, адрес и положительная сумма.")
        self._status = OrderStatus.PLACED

    def cancel(self) -> None:
        if self._status is OrderStatus.CANCELLED:
            raise OrderStateError("Заказ уже отменён.")
        self._status = OrderStatus.CANCELLED
