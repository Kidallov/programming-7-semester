import unittest


@unittest.skip("Этап 2 ещё не реализован.")
class OrderSellerTests(unittest.TestCase):
    def test_line_id_is_unique_and_first_seller_rejects_another_seller(self) -> None:
        self.fail("Добавить правило одного продавца и уникальность OrderLineId.")
