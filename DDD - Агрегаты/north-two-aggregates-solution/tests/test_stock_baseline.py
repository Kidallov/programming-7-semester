import unittest

from north_marketplace.domain.errors import InsufficientStockError, InvalidValueError
from north_marketplace.domain.identifiers import StockItemId, WarehouseId
from north_marketplace.domain.stock_item import StockItem
from north_marketplace.domain.values import Quantity, Sku, StockBalance


def make_stock(balance=8):
    return StockItem(StockItemId("stock-1"), WarehouseId("warehouse-1"),
                     Sku("BOOK"), StockBalance(balance))


class StockBaselineTests(unittest.TestCase):
    def test_receive_and_write_off_to_zero(self):
        stock = make_stock(0)
        stock.receive(Quantity(5))
        old_balance = stock.physical_balance()
        stock.write_off(Quantity(5))
        self.assertEqual(old_balance, StockBalance(5))
        self.assertEqual(stock.physical_balance(), StockBalance(0))
        self.assertEqual(stock.available_quantity(), StockBalance(0))
        self.assertEqual(stock.id(), StockItemId("stock-1"))
        self.assertEqual(stock.warehouse_id(), WarehouseId("warehouse-1"))
        self.assertEqual(stock.sku(), Sku("BOOK"))

    def test_overdraw_rejected_without_change(self):
        stock = make_stock(2)
        with self.assertRaises(InsufficientStockError):
            stock.write_off(Quantity(3))
        self.assertEqual(stock.physical_balance(), StockBalance(2))
        self.assertEqual(stock.available_quantity(), StockBalance(2))

    def test_balance_validation_and_immutability(self):
        for value in (-1, True, 2.5, "2"):
            with self.subTest(value=value), self.assertRaises(InvalidValueError):
                StockBalance(value)
        balance = StockBalance(0)
        with self.assertRaises(InvalidValueError):
            balance.decrease(Quantity(1))
        with self.assertRaises(AttributeError):
            balance._value = 10

    def test_raw_quantities_are_not_accepted(self):
        stock = make_stock()
        for action in (stock.receive, stock.write_off):
            with self.assertRaises(InvalidValueError):
                action(1)
        self.assertEqual(stock.physical_balance(), StockBalance(8))
