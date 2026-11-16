import unittest
from datetime import datetime, timedelta, timezone

from north_marketplace.domain.errors import DuplicateReservationError, InvalidValueError, ReservationStateError
from north_marketplace.domain.identifiers import OrderId, ReservationId
from north_marketplace.domain.values import Quantity, ReservationDeadline, ReservationStatus, StockBalance
from test_stock_baseline import make_stock


def moment(hour):
    return datetime(2026, 5, 20, hour, tzinfo=timezone.utc)


def timed_reserve(stock, name, hour, quantity=1):
    stock.reserve(ReservationId(name), OrderId("o-1"), Quantity(quantity), ReservationDeadline(moment(hour)))


class StockExpirationTests(unittest.TestCase):
    def test_expiry_at_exact_deadline_preserves_physical_and_snapshot(self):
        stock = make_stock()
        timed_reserve(stock, "r-1", 12, 3)
        old = stock.reservations()
        self.assertEqual(stock.expire_reservations(moment(11)), 0)
        self.assertEqual(stock.available_quantity(), StockBalance(5))
        self.assertEqual(stock.expire_reservations(moment(12)), 1)
        self.assertEqual(stock.available_quantity(), StockBalance(8))
        self.assertEqual(stock.physical_balance(), StockBalance(8))
        self.assertEqual(len(stock.reservations()), 1)
        self.assertEqual(stock.reservations()[0].status(), ReservationStatus.EXPIRED)
        self.assertEqual(old[0].status(), ReservationStatus.ACTIVE)
        self.assertEqual(stock.expire_reservations(moment(12)), 0)

    def test_mixed_reservations_count_only_due_active_records(self):
        stock = make_stock(10)
        timed_reserve(stock, "past", 10, 2)
        timed_reserve(stock, "exact", 12, 2)
        timed_reserve(stock, "future", 13, 2)
        timed_reserve(stock, "released", 10, 2)
        stock.release_reservation(ReservationId("released"))
        self.assertEqual(stock.expire_reservations(moment(12)), 2)
        self.assertEqual([r.status() for r in stock.reservations()], [
            ReservationStatus.EXPIRED, ReservationStatus.EXPIRED,
            ReservationStatus.ACTIVE, ReservationStatus.RELEASED,
        ])
        self.assertEqual(stock.available_quantity(), StockBalance(8))
        self.assertEqual(stock.physical_balance(), StockBalance(10))
        self.assertEqual(len(stock.reservations()), 4)

    def test_invalid_time_is_rejected_before_any_mutation(self):
        stock = make_stock()
        timed_reserve(stock, "r-1", 10)
        for value in (datetime(2026, 5, 20, 12), "2026-05-20", None):
            before = stock.reservations()
            with self.subTest(value=value):
                with self.assertRaises(InvalidValueError):
                    ReservationDeadline(value)
                with self.assertRaises(InvalidValueError):
                    stock.expire_reservations(value)
                self.assertEqual(stock.reservations(), before)

    def test_equivalent_timezones_represent_same_deadline(self):
        stock = make_stock()
        timed_reserve(stock, "r-1", 12)
        moscow_time = datetime(2026, 5, 20, 15, tzinfo=timezone(timedelta(hours=3)))
        self.assertEqual(stock.expire_reservations(moscow_time), 1)
        self.assertEqual(ReservationDeadline(moment(12)), ReservationDeadline(moscow_time))

    def test_expired_reservation_cannot_be_released_or_reused(self):
        stock = make_stock()
        timed_reserve(stock, "r-1", 10)
        stock.expire_reservations(moment(12))
        before = stock.reservations()
        with self.assertRaises(ReservationStateError):
            stock.release_reservation(ReservationId("r-1"))
        with self.assertRaises(DuplicateReservationError):
            timed_reserve(stock, "r-1", 13)
        self.assertEqual(stock.reservations(), before)

    def test_empty_stock_has_no_expirations(self):
        self.assertEqual(make_stock().expire_reservations(moment(12)), 0)

    def test_deadline_is_immutable(self):
        deadline = ReservationDeadline(moment(12))
        with self.assertRaises(AttributeError):
            deadline._moment = moment(13)
        self.assertEqual(deadline.moment(), moment(12))
