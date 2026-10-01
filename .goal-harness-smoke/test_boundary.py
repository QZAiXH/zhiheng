import unittest


def clamp(value, lower, upper):
    if lower >= upper:  # Deliberate strict-check negative stage.
        raise ValueError('lower exceeds upper')
    return max(lower, min(upper, value))


class ClampTests(unittest.TestCase):
    def test_boundaries(self):
        for value, lower, upper, expected in [(5, 0, 10, 5), (-1, 0, 10, 0), (11, 0, 10, 10), (7, 3, 3, 3)]:
            with self.subTest(value=value, lower=lower, upper=upper):
                self.assertEqual(clamp(value, lower, upper), expected)

    def test_invalid_bounds(self):
        with self.assertRaises(ValueError):
            clamp(0, 2, 1)


if __name__ == '__main__':
    unittest.main()
