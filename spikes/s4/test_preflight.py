import subprocess
import sys
import unittest
from types import SimpleNamespace

from preflight import engine_gate, inspect_wsl


class PreflightTests(unittest.TestCase):
    def test_claimed_ready_cannot_enable_engine_launch(self):
        for value in (None, {}, {'ready': True, 'engine': '/fake/podman', 'cleanup_ok': True}):
            self.assertEqual(engine_gate(value)['launchGate'], 'BLOCKED')
            self.assertFalse(engine_gate(value)['hostFallback'])

    def test_timeout_and_missing_tool_are_unknown_blocked(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('wsl', 25)):
            def runner(*args, **kwargs):
                raise error
            result = inspect_wsl(runner)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['launchGate'], 'BLOCKED')

    def test_malformed_or_forged_external_discovery_is_blocked(self):
        for raw in (b'not json', b'[]', b'{"platform":"linux","launchGate":"READY"}', b'x' * 32769):
            result = inspect_wsl(lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=raw))
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['launchGate'], 'BLOCKED')

    def test_direct_windows_collector_has_no_unsafe_fallback(self):
        if sys.platform != 'win32':
            self.skipTest('Windows capability-denial check')
        from collector import PrivateCollector, Blocked
        with self.assertRaises(Blocked) as result:
            PrivateCollector(0, (0, 0), {})
        self.assertEqual(result.exception.code, 'E_CAPABILITY')


if __name__ == '__main__':
    unittest.main()
