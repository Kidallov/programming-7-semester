import unittest
from datetime import datetime, timezone

from north_marketplace.domain.errors import (
    DuplicateReservationError, InsufficientStockError, InvalidValueError,
    ReservationNotFoundError, ReservationStateError,
)
from north_marketplace.domain.identifiers import OrderId, ReservationId
from north_marketplace.domain.values import Quantity, ReservationDeadline, ReservationStatus, StockBalance
from test_order_baseline import make_order
from test_stock_baseline import make_stock


def deadline():
    return ReservationDeadline(datetime(2026, 5, 20, 12, tzinfo=timezone.utc))


def reserve(stock, reservation_id="r-1", quantity=3):
    stock.reserve(ReservationId(reservation_id), OrderId("o-1"), Quantity(quantity), deadline())


class StockReservationTests(unittest.TestCase):
    def test_reserve_changes_available_not_physical_balance(self):
        stock = make_stock()
        reserve(stock)
        self.assertEqual(stock.physical_balance(), StockBalance(8))
        self.assertEqual(stock.active_reserved_quantity(), StockBalance(3))
        self.assertEqual(stock.available_quantity(), StockBalance(5))
        summary = stock.reservations()[0]
        self.assertEqual(summary.order_id(), OrderId("o-1"))
        self.assertEqual(summary.status(), ReservationStatus.ACTIVE)

    def test_exact_available_amount_can_be_reserved(self):
        stock = make_stock()
        reserve(stock, quantity=8)
        self.assertEqual(stock.available_quantity(), StockBalance(0))

    def test_excess_reservation_is_atomic(self):
        stock = make_stock()
        reserve(stock, quantity=7)
        before = (stock.reservations(), stock.physical_balance(), stock.available_quantity())
        with self.assertRaises(InsufficientStockError):
            reserve(stock, "r-2", 2)
        self.assertEqual((stock.reservations(), stock.physical_balance(), stock.available_quantity()), before)

    def test_release_preserves_record_and_old_snapshot(self):
        stock = make_stock()
        reserve(stock)
        old = stock.reservations()
        stock.release_reservation(ReservationId("r-1"))
        self.assertIsInstance(old, tuple)
        self.assertEqual(len(stock.reservations()), 1)
        self.assertEqual(old[0].status(), ReservationStatus.ACTIVE)
        self.assertEqual(stock.reservations()[0].status(), ReservationStatus.RELEASED)
        self.assertEqual(stock.available_quantity(), StockBalance(8))
        self.assertEqual(stock.active_reserved_quantity(), StockBalance(0))
        with self.assertRaises(AttributeError):
            old[0]._status = ReservationStatus.RELEASED

    def test_duplicate_id_even_after_release_is_rejected(self):
        stock = make_stock()
        reserve(stock)
        for released in (False, True):
            if released:
                stock.release_reservation(ReservationId("r-1"))
            before = stock.reservations()
            with self.assertRaises(DuplicateReservationError):
                reserve(stock)
            self.assertEqual(stock.reservations(), before)

    def test_unknown_and_repeated_release_are_rejected(self):
        stock = make_stock()
        reserve(stock)
        before = stock.reservations()
        with self.assertRaises(ReservationNotFoundError):
            stock.release_reservation(ReservationId("missing"))
        self.assertEqual(stock.reservations(), before)
        stock.release_reservation(ReservationId("r-1"))
        before = stock.reservations()
        with self.assertRaises(ReservationStateError):
            stock.release_reservation(ReservationId("r-1"))
        self.assertEqual(stock.reservations(), before)

    def test_write_off_protects_active_reservations(self):
        stock = make_stock()
        reserve(stock, quantity=5)
        stock.receive(Quantity(2))
        stock.write_off(Quantity(5))
        before = (stock.physical_balance(), stock.reservations())
        with self.assertRaises(InsufficientStockError):
            stock.write_off(Quantity(1))
        self.assertEqual((stock.physical_balance(), stock.reservations()), before)
        self.assertEqual(stock.available_quantity(), StockBalance(0))

    def test_order_object_is_not_accepted_instead_of_id(self):
        stock = make_stock()
        with self.assertRaises(InvalidValueError):
            stock.reserve(ReservationId("r-1"), make_order(), Quantity(1), deadline())
        self.assertEqual(stock.reservations(), ())

    def test_only_active_records_contribute_to_available_balance(self):
        stock = make_stock()
        reserve(stock, "r-1", 2)
        reserve(stock, "r-2", 3)
        stock.release_reservation(ReservationId("r-1"))
        self.assertEqual(stock.active_reserved_quantity(), StockBalance(3))
        self.assertEqual(stock.available_quantity(), StockBalance(5))
