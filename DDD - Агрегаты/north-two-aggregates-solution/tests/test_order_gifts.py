import unittest
from decimal import Decimal

from north_marketplace.domain.errors import (
    DuplicateOrderLineError, IncompleteOrderError, InvalidValueError,
    OrderStateError, SellerMismatchError,
)
from north_marketplace.domain.identifiers import OrderLineId, SellerId
from north_marketplace.domain.order import OrderLine
from north_marketplace.domain.values import Currency, LineKind, Money, Quantity, Sku
from test_order_baseline import add_line, address, make_order


def add_gift(order, line_id="gift", seller="seller-1"):
    order.add_gift_line(OrderLineId(line_id), Sku("GIFT"), "Закладка", SellerId(seller), Quantity(1))


class OrderGiftTests(unittest.TestCase):
    def test_paid_line_and_gift_can_be_placed_with_unchanged_total(self):
        order = make_order()
        add_line(order)
        before = order.total()
        add_gift(order)
        gift = order.lines()[1]
        self.assertEqual(gift.kind(), LineKind.GIFT)
        self.assertEqual(gift.unit_price(), Money(Decimal("0"), order.currency()))
        self.assertEqual(gift.subtotal().amount(), Decimal("0"))
        self.assertEqual(order.total(), before)
        order.set_shipping_address(address())
        order.place()

    def test_only_gifts_cannot_be_placed(self):
        order = make_order()
        add_gift(order)
        order.set_shipping_address(address())
        before = (order.lines(), order.status(), order.total())
        with self.assertRaises(IncompleteOrderError):
            order.place()
        self.assertEqual((order.lines(), order.status(), order.total()), before)
        add_line(order)
        order.place()

    def test_paid_line_rejects_zero_price_without_mutation(self):
        order = make_order()
        with self.assertRaises(InvalidValueError):
            add_line(order, amount="0")
        self.assertEqual(order.lines(), ())
        self.assertIsNone(order.seller_id())

    def test_internal_line_rejects_price_incompatible_with_kind(self):
        for kind, amount in ((LineKind.GIFT, "1"), (LineKind.PAID, "0")):
            with self.subTest(kind=kind), self.assertRaises(InvalidValueError):
                OrderLine(OrderLineId("x"), Sku("X"), "Название", SellerId("s"),
                          Money(Decimal(amount), Currency("RUB")), Quantity(1), kind)

    def test_gift_obeys_seller_uniqueness_and_status(self):
        order = make_order()
        add_line(order)
        before = order.lines()
        with self.assertRaises(SellerMismatchError):
            add_gift(order, seller="other")
        with self.assertRaises(DuplicateOrderLineError):
            add_gift(order, line_id="l-1")
        self.assertEqual(order.lines(), before)
        order.set_shipping_address(address())
        order.place()
        with self.assertRaises(OrderStateError):
            add_gift(order)
        self.assertEqual(order.lines(), before)

    def test_gift_snapshot_is_immutable_and_independent(self):
        order = make_order()
        add_gift(order)
        snapshot = order.lines()[0]
        order.change_line_quantity(snapshot.id(), Quantity(4))
        self.assertEqual(snapshot.quantity(), Quantity(1))
        self.assertEqual(order.lines()[0].quantity(), Quantity(4))
        with self.assertRaises(AttributeError):
            snapshot._kind = LineKind.PAID
