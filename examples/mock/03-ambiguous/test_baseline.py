import unittest
from after import save_name
class Baseline(unittest.TestCase):
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            save_name('')
    def test_normal_preserved(self):
        self.assertEqual(save_name('Ada'), 'Ada')
