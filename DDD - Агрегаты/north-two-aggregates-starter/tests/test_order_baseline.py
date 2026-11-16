import unittest


@unittest.skip("Этап 1 ещё не реализован.")
class OrderBaselineTests(unittest.TestCase):
    def test_line_id_changes_quantity_and_place_requires_full_order(self) -> None:
        self.fail("Реализовать базовый Order, OrderLineId и снимки строк.")
