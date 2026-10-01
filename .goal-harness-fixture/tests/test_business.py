import unittest
import solution

class Business(unittest.TestCase):
    def test_behavior(self):
        self.assertEqual(solution.divide(8, 2), 4)
        with self.assertRaisesRegex(ValueError, 'zero divisor'):
            solution.divide(1, 0)
