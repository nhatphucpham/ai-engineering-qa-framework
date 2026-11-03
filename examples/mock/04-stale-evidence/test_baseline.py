import unittest
from before import can_reserve
class Baseline(unittest.TestCase):
    def test_within_stock(self):
        self.assertTrue(can_reserve(5, 3))
    def test_over_stock(self):
        self.assertFalse(can_reserve(5, 6))
