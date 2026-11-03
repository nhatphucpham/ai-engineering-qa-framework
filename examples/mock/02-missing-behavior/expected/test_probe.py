import unittest
from after import apply_filter
class Probe(unittest.TestCase):
    def test_resets_page(self):
        self.assertEqual(apply_filter(['alpha', 'beta'], 'alpha', 3)['page'], 1)
