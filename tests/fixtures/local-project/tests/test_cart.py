import unittest
from decimal import Decimal

from cart import subtotal


class CartTests(unittest.TestCase):
    def test_existing_subtotal(self):
        self.assertEqual(subtotal([(2, "1.25"), (1, "0.50")]), Decimal("3.00"))


if __name__ == "__main__":
    unittest.main()
