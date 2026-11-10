"""Check that the differential harness cannot mark missing/unsafe evidence green."""

import copy
import unittest

from run_s1 import assert_corpus, cases, first_diff, matches


class S1HarnessTests(unittest.TestCase):
    def test_required_denominators_and_ids_cannot_disappear(self):
        requests = cases()
        assert_corpus(requests)
        missing = [r for r in requests if r['id'] != next(v['id'] for v in requests if v['group'] == 'p1-valid')]
        with self.assertRaises(ValueError):
            assert_corpus(missing)
        with self.assertRaises(ValueError):
            assert_corpus(requests + [requests[0]])

    def test_shared_failure_is_not_a_valid_detachment_or_repeatability_check(self):
        request = {'id': 'test', 'op': 'detachment'}
        bad = {'id': 'test', 'kind': 'ok', 'value': False, 'noMutation': True, 'repeatable': True}
        self.assertFalse(matches(request, bad, bad))
        good = dict(bad, value=True)
        self.assertTrue(matches(request, good, good))
        for change in ({'noMutation': False}, {'repeatable': False}, {'id': 'wrong'}):
            changed = {**good, **change}
            self.assertFalse(matches(request, changed, changed))
        self.assertEqual(first_diff({'number': 1}, {'number': 1.0}), '/number')


if __name__ == '__main__':
    unittest.main()
