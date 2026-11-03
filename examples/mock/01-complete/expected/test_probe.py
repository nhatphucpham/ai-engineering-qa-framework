import unittest
from after import shipping
class Probe(unittest.TestCase):
    def test_above_threshold(self):
        self.assertEqual(shipping(101), 0)
