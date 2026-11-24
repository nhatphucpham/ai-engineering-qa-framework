"""Partial startup/bookkeeping failures must not skip independent DB cleanup."""
from unittest.mock import Mock
import unittest

from .lifecycle import finish


class CleanupTests(unittest.TestCase):
    def test_partial_startup_still_stops_running_cluster(self):
        evidence = {'status': 'ERROR', 'inputsBefore': {}}
        stop = Mock(return_value={'statusCode': 3})
        finish(evidence, attempted=True, close=lambda: None, pins=lambda: {},
               observe=Mock(side_effect=['RUNNING', 'STOPPED']), stop=stop)
        stop.assert_called_once()
        self.assertTrue(evidence['databaseStopped'])
        self.assertEqual(evidence['status'], 'ERROR')

    def test_close_and_hash_errors_do_not_skip_stop(self):
        evidence = {'status': 'PASS', 'inputsBefore': {}}
        stop = Mock(return_value={'statusCode': 3})
        finish(evidence, attempted=True, close=Mock(side_effect=OSError()), pins=Mock(side_effect=ValueError()),
               observe=Mock(side_effect=['RUNNING', 'STOPPED']), stop=stop)
        stop.assert_called_once()
        self.assertTrue(evidence['databaseStopped'])
        self.assertEqual(evidence['status'], 'ERROR')
        self.assertEqual([row['stage'] for row in evidence['finalizationErrors']], ['close', 'inputsAfter'])

    def test_cleanup_failure_never_claims_stopped(self):
        evidence = {'status': 'PASS', 'inputsBefore': {}}
        finish(evidence, attempted=True, close=lambda: None, pins=lambda: {},
               observe=lambda: 'RUNNING', stop=Mock(side_effect=OSError()))
        self.assertFalse(evidence['databaseStopped'])
        self.assertEqual(evidence['status'], 'ERROR')

    def test_no_launch_or_already_stopped_does_not_stop_unowned_service(self):
        for attempted in (False, True):
            evidence = {'status': 'ERROR', 'inputsBefore': {}}
            stop = Mock(); observe = Mock(return_value='STOPPED')
            finish(evidence, attempted=attempted, close=lambda: None, pins=lambda: {}, observe=observe, stop=stop)
            stop.assert_not_called()
            if not attempted:
                observe.assert_not_called()
            self.assertEqual(evidence['databaseStopped'], True if attempted else None)
