"""A ready proposal observed after its bound must remain unaccepted."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from .common import Error
from .run_fresh import await_native_ready, require_native_deadline


class NativeDeadlineTests(unittest.TestCase):
    def test_preexisting_ready_does_not_bypass_expired_window(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'native-ready-1.json'; path.write_bytes(b'{}')
            renew = Mock()
            with patch('runtime_candidate.run_fresh.time.monotonic', return_value=121):
                with self.assertRaises(Error):
                    await_native_ready(path, 120, renew)
            renew.assert_not_called()

    def test_validation_crossing_deadline_cannot_be_accepted(self):
        with patch('runtime_candidate.run_fresh.time.monotonic', side_effect=[119, 121]):
            require_native_deadline(120)
            with self.assertRaises(Error):
                require_native_deadline(120)


if __name__ == '__main__':
    unittest.main()
