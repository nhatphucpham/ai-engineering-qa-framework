import unittest

from pricing import payable


class Baseline(unittest.TestCase):
    def test_below_threshold(self):
        self.assertEqual(payable(70_000, 20_000), 90_000)

    def test_above_threshold_without_shipping(self):
        self.assertEqual(payable(150_000, 0), 135_000)
