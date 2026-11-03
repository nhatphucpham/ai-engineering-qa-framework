import unittest
from after import can_reserve
class Probe(unittest.TestCase):
    def test_over_stock_at_head(self):
        self.assertFalse(can_reserve(5, 6))
