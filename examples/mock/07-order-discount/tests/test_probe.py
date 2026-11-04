import unittest

from pricing import payable


class Probe(unittest.TestCase):
    def test_threshold_is_inclusive(self):
        self.assertEqual(payable(100_000, 0), 90_000)

    def test_shipping_is_not_discounted(self):
        self.assertEqual(payable(150_000, 20_000), 155_000)
