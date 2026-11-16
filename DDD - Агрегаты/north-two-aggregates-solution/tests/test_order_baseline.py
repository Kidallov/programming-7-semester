import unittest
from decimal import Decimal

from north_marketplace.domain.errors import (
    CurrencyMismatchError, IncompleteOrderError, InvalidValueError,
    OrderLineNotFoundError, OrderStateError,
)
from north_marketplace.domain.identifiers import BuyerId, OrderId, OrderLineId, SellerId
from north_marketplace.domain.order import Order
from north_marketplace.domain.values import Currency, Money, OrderStatus, Quantity, ShippingAddress, Sku


def address():
    return ShippingAddress("Архангельск", "Поморская", "18", "163000")


def make_order():
    return Order(OrderId("o-1"), BuyerId("b-1"), Currency("RUB"))


def add_line(order, line_id="l-1", currency="RUB", amount="100", quantity=1):
    order.add_paid_line(OrderLineId(line_id), Sku("BOOK"), "Книга", SellerId("seller-1"),
                   Money(Decimal(amount), Currency(currency)), Quantity(quantity))


class OrderBaselineTests(unittest.TestCase):
    def test_values_reject_invalid_input(self):
        for value in (0, -1, True, 1.5, "1"):
            with self.subTest(quantity=value), self.assertRaises(InvalidValueError):
                Quantity(value)
        for value in ("", "  ", 123):
            for cls in (OrderId, OrderLineId, BuyerId, Sku, Currency):
                with self.subTest(cls=cls, value=value), self.assertRaises(InvalidValueError):
                    cls(value)
        for value in ("RU", "R1B", "РУБ", "RUBB"):
            with self.assertRaises(InvalidValueError):
                Currency(value)
        for value in (Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), 10.0):
            with self.assertRaises(InvalidValueError):
                Money(value, Currency("RUB"))
        for index in range(4):
            fields = ["город", "улица", "дом", "индекс"]
            fields[index] = " "
            with self.assertRaises(InvalidValueError):
                ShippingAddress(*fields)

    def test_values_have_typed_equality_and_are_immutable(self):
        self.assertEqual(OrderId(" x "), OrderId("x"))
        self.assertNotEqual(OrderId("x"), BuyerId("x"))
        self.assertEqual(Currency(" rub "), Currency("RUB"))
        self.assertEqual(hash(OrderId("x")), hash(OrderId("x")))
        for value, field in ((OrderId("x"), "_value"), (Quantity(1), "_value"),
                             (Money(Decimal("1"), Currency("RUB")), "_amount"),
                             (address(), "_city")):
            with self.assertRaises(AttributeError):
                setattr(value, field, None)
            with self.assertRaises(AttributeError):
                delattr(value, field)

    def test_money_arithmetic_preserves_currency_and_original(self):
        money = Money(Decimal("0.10"), Currency("RUB"))
        self.assertEqual(money.multiply(Quantity(3)).amount(), Decimal("0.30"))
        self.assertEqual(money.add(money).amount(), Decimal("0.20"))
        self.assertEqual(money.amount(), Decimal("0.10"))
        with self.assertRaises(CurrencyMismatchError):
            money.add(Money(Decimal("1"), Currency("USD")))

    def test_place_requires_lines_address_and_positive_total(self):
        order = make_order()
        with self.assertRaises(IncompleteOrderError):
            order.place()
        add_line(order)
        before = order.lines()
        with self.assertRaises(IncompleteOrderError):
            order.place()
        self.assertEqual(order.status(), OrderStatus.DRAFT)
        self.assertEqual(order.lines(), before)
        order.set_shipping_address(address())
        order.place()
        self.assertEqual(order.status(), OrderStatus.PLACED)
        self.assertEqual(order.total().amount(), Decimal("100"))

    def test_currency_rejection_leaves_order_unchanged(self):
        order = make_order()
        add_line(order)
        before = (order.lines(), order.total(), order.status())
        with self.assertRaises(CurrencyMismatchError):
            add_line(order, "l-2", "USD")
        self.assertEqual((order.lines(), order.total(), order.status()), before)

    def test_change_quantity_by_id_preserves_old_snapshot(self):
        order = make_order()
        add_line(order)
        add_line(order, "l-2", amount="20")
        old = order.lines()
        order.change_line_quantity(OrderLineId("l-1"), Quantity(3))
        self.assertIsInstance(old, tuple)
        self.assertEqual(old[0].quantity(), Quantity(1))
        self.assertEqual(order.lines()[0].quantity(), Quantity(3))
        self.assertEqual(order.lines()[1].quantity(), Quantity(1))
        self.assertEqual(order.total().amount(), Decimal("320"))
        with self.assertRaises(AttributeError):
            old[0]._quantity = Quantity(99)
        before = order.lines()
        with self.assertRaises(OrderLineNotFoundError):
            order.change_line_quantity(OrderLineId("missing"), Quantity(2))
        self.assertEqual(order.lines(), before)

    def test_placed_and_cancelled_orders_reject_editing(self):
        for placed in (False, True):
            order = make_order()
            add_line(order)
            order.set_shipping_address(address())
            if placed:
                order.place()
            else:
                order.cancel()
            before = (order.lines(), order.shipping_address(), order.status())
            for action in (lambda: add_line(order, "l-2"),
                           lambda: order.change_line_quantity(OrderLineId("l-1"), Quantity(2)),
                           lambda: order.set_shipping_address(address()), order.place):
                with self.assertRaises(OrderStateError):
                    action()
                self.assertEqual((order.lines(), order.shipping_address(), order.status()), before)

    def test_cancel_draft_or_placed_but_not_twice(self):
        for placed in (False, True):
            order = make_order()
            if placed:
                add_line(order)
                order.set_shipping_address(address())
                order.place()
            order.cancel()
            self.assertEqual(order.status(), OrderStatus.CANCELLED)
            with self.assertRaises(OrderStateError):
                order.cancel()

    def test_wrong_identifier_type_is_rejected(self):
        with self.assertRaises(InvalidValueError):
            Order(BuyerId("x"), BuyerId("b"), Currency("RUB"))

    def test_address_does_not_make_empty_order_placeable(self):
        order = make_order()
        order.set_shipping_address(address())
        with self.assertRaises(IncompleteOrderError):
            order.place()
        self.assertEqual(order.status(), OrderStatus.DRAFT)
        self.assertEqual(order.lines(), ())
        self.assertEqual(order.shipping_address(), address())

    def test_invalid_title_does_not_fix_seller_or_add_line(self):
        order = make_order()
        with self.assertRaises(InvalidValueError):
            order.add_paid_line(OrderLineId("l-1"), Sku("BOOK"), " ", SellerId("s"),
                                Money(Decimal("10"), Currency("RUB")), Quantity(1))
        self.assertIsNone(order.seller_id())
        self.assertEqual(order.lines(), ())
