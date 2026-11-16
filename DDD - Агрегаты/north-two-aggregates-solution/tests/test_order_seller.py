import unittest
from decimal import Decimal

from north_marketplace.domain.errors import CurrencyMismatchError, DuplicateOrderLineError, SellerMismatchError
from north_marketplace.domain.identifiers import OrderLineId, SellerId
from north_marketplace.domain.values import Currency, Money, Quantity, Sku
from test_order_baseline import add_line, make_order


class OrderSellerTests(unittest.TestCase):
    def test_same_seller_can_add_another_line(self):
        order = make_order()
        self.assertIsNone(order.seller_id())
        add_line(order)
        add_line(order, "l-2")
        self.assertEqual(order.seller_id(), SellerId("seller-1"))
        self.assertEqual(len(order.lines()), 2)

    def test_second_seller_rejected_without_change(self):
        order = make_order()
        add_line(order)
        before = (order.lines(), order.total(), order.seller_id())
        with self.assertRaises(SellerMismatchError):
            order.add_paid_line(OrderLineId("l-2"), Sku("BOOK"), "Книга", SellerId("other"),
                           Money(Decimal("10"), Currency("RUB")), Quantity(1))
        self.assertEqual((order.lines(), order.total(), order.seller_id()), before)

    def test_duplicate_line_id_rejected_without_change(self):
        order = make_order()
        add_line(order)
        before = order.lines()
        with self.assertRaises(DuplicateOrderLineError):
            add_line(order)
        self.assertEqual(order.lines(), before)

    def test_invalid_first_line_does_not_fix_seller(self):
        order = make_order()
        with self.assertRaises(CurrencyMismatchError):
            add_line(order, currency="USD")
        self.assertIsNone(order.seller_id())
        self.assertEqual(order.lines(), ())
