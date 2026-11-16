"""Детерминированная координация двух корней без дублирования их правил."""

from datetime import datetime, timezone
from decimal import Decimal

from .domain.identifiers import (
    BuyerId, OrderId, OrderLineId, ReservationId, SellerId, StockItemId, WarehouseId,
)
from .domain.order import Order
from .domain.stock_item import StockItem
from .domain.values import Currency, Money, Quantity, ReservationDeadline, ShippingAddress, Sku, StockBalance


def run_demo() -> str:
    rub = Currency("RUB")
    order = Order(OrderId("order-100"), BuyerId("buyer-20"), rub)
    seller_id = SellerId("seller-7")
    order.add_paid_line(
        OrderLineId("line-1"), Sku("BOOK-001"), "Книга о Севере", seller_id,
        Money(Decimal("1290.00"), rub), Quantity(1),
    )
    order.add_gift_line(
        OrderLineId("line-2"), Sku("BOOKMARK-001"), "Закладка", seller_id, Quantity(1),
    )
    order.set_shipping_address(ShippingAddress("Архангельск", "Поморская", "18", "163000"))
    order.place()

    stock_item = StockItem(
        StockItemId("stock-400"), WarehouseId("warehouse-ark"), Sku("BOOK-001"), StockBalance(8),
    )
    deadline = ReservationDeadline(datetime(2026, 5, 20, 12, tzinfo=timezone.utc))
    stock_item.reserve(ReservationId("reservation-900"), order.id(), Quantity(1), deadline)

    return "\n".join((
        f"Заказ: {order.id().value()}",
        f"Состояние: {order.status().value}",
        f"Сумма: {order.total()}",
        f"Физический остаток: {stock_item.physical_balance().value()}",
        f"Доступный остаток: {stock_item.available_quantity().value()}",
        f"Резерв reservation-900 создан по OrderId({order.id().value()}).",
    ))


def main() -> int:
    print(run_demo())
    return 0
