import unittest
from after import can_delete
class Probe(unittest.TestCase):
    def test_cross_workspace_denied(self):
        self.assertFalse(can_delete('admin', False))
