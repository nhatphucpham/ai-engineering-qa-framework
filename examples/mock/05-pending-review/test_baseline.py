import unittest
from after import can_delete
class Baseline(unittest.TestCase):
    def test_admin_same_workspace(self):
        self.assertTrue(can_delete('admin', True))
    def test_non_admin_denied(self):
        for role in ['member', 'viewer', '', 'unknown']:
            with self.subTest(role=role):
                self.assertFalse(can_delete(role, True))
