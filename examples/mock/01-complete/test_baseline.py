import unittest
from after import shipping
class Baseline(unittest.TestCase):
    def test_below_threshold(self):
        self.assertEqual(shipping(20), 5)
    def test_exact_threshold(self):
        self.assertEqual(shipping(100), 0)
