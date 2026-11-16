import io
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from north_marketplace.application import main, run_demo
from north_marketplace.domain.errors import InsufficientStockError
from north_marketplace.domain.identifiers import OrderId, ReservationId
from north_marketplace.domain.order import Order
from north_marketplace.domain.stock_item import StockItem
from north_marketplace.domain.values import OrderStatus, Quantity
from test_order_baseline import add_line, address, make_order
from test_stock_baseline import make_stock
from test_stock_reservations import deadline


EXPECTED = "\n".join((
    "Заказ: order-100",
    "Состояние: PLACED",
    "Сумма: 1290.00 RUB",
    "Физический остаток: 8",
    "Доступный остаток: 7",
    "Резерв reservation-900 создан по OrderId(order-100).",
))


class DemoTests(unittest.TestCase):
    def test_demo_is_deterministic_and_returns_text(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run_demo(), EXPECTED)
            self.assertEqual(run_demo(), EXPECTED)
        self.assertEqual(output.getvalue(), "")

    def test_main_prints_result_and_returns_success(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertEqual(output.getvalue(), EXPECTED + "\n")

    def test_cli_runs_without_input(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "north_marketplace"],
            cwd=Path(__file__).resolve().parents[1], input="", capture_output=True,
            text=True, encoding="utf-8", timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED + "\n")
        self.assertEqual(result.stderr, "")

    def test_demo_places_before_reserving_and_passes_only_order_id(self):
        calls = []
        original_place = Order.place
        original_reserve = StockItem.reserve

        def place(order):
            original_place(order)
            calls.append(("placed", order.id()))

        def reserve(stock, reservation_id, order_id, quantity, deadline):
            self.assertIsInstance(order_id, OrderId)
            self.assertEqual(calls, [("placed", order_id)])
            original_reserve(stock, reservation_id, order_id, quantity, deadline)
            calls.append(("reserved", order_id))

        with patch.object(Order, "place", place), patch.object(StockItem, "reserve", reserve):
            self.assertEqual(run_demo(), EXPECTED)
        self.assertEqual([name for name, _ in calls], ["placed", "reserved"])

    def test_placing_does_not_reserve_and_failed_reserve_does_not_cancel_order(self):
        order = make_order()
        stock = make_stock(0)
        add_line(order)
        order.set_shipping_address(address())
        order.place()
        self.assertEqual(stock.reservations(), ())
        before = (order.status(), order.lines(), order.total())
        with self.assertRaises(InsufficientStockError):
            stock.reserve(ReservationId("r-1"), order.id(), Quantity(1), deadline())
        self.assertEqual(order.status(), OrderStatus.PLACED)
        self.assertEqual((order.status(), order.lines(), order.total()), before)
        self.assertEqual(stock.reservations(), ())
