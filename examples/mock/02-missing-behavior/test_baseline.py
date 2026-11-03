import unittest
from after import apply_filter
class Baseline(unittest.TestCase):
    def test_matching_rows(self):
        self.assertEqual(apply_filter(['alpha', 'beta'], 'alpha', 1)['rows'], ['alpha'])
    def test_no_matches(self):
        self.assertEqual(apply_filter(['alpha'], 'none', 1)['rows'], [])
