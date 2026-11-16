import unittest


@unittest.skip("Этап 4 ещё не реализован.")
class StockBaselineTests(unittest.TestCase):
    def test_physical_balance_never_becomes_negative(self) -> None:
        self.fail("Реализовать базовый агрегат StockItem.")
