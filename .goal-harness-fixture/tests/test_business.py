import unittest
import solution

class Business(unittest.TestCase):
    def test_behavior(self):
        self.assertEqual(solution.add(2, 3), 5)
        self.assertEqual(solution.add(-2, 3), 1)
        self.assertEqual(solution.double_sum(2, 3), 10)
