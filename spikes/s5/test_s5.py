import copy
import json
import unittest
from pathlib import Path
from normalizer import Reconciler, observe_timeline, observe_webhook, observe_snapshot

FIX = json.loads((Path(__file__).parent / "provider-shapes.json").read_text(encoding="utf-8-sig"))
A = "a" * 40
B = "b" * 40


class OfflineConformance(unittest.TestCase):
    def test_raw_duplicate_and_no_crosswalk(self):
        w = observe_webhook(FIX["webhook"], "delivery-1")
        self.assertEqual(w, observe_webhook(FIX["webhook"], "delivery-1"))
        t = observe_timeline(42, 7, FIX["timeline"])
        self.assertEqual((w["status"], t["status"]), ("unresolved", "unresolved"))
        self.assertNotIn("normalizedKey", w)
        self.assertNotIn("normalizedKey", t)

    def test_duplicate_cross_ingress_assumption(self):
        r = Reconciler()
        self.assertEqual(r.bind_test_assertion("p", 42, 7, 101, A)["status"], "resolved")
        self.assertEqual(r.bind_test_assertion("p", 42, 7, 101, A)["status"], "duplicate")
        self.assertEqual(len(r.intents), 1)

    def test_second_ready_same_sha(self):
        r = Reconciler()
        x = r.bind_test_assertion("p", 42, 7, 101, A)
        y = r.bind_test_assertion("p", 42, 7, 102, A)
        self.assertNotEqual(x["normalizedKey"], y["normalizedKey"])
        self.assertEqual(len(r.intents), 2)

    def test_delayed_and_gap(self):
        self.assertEqual(FIX["current_pull"]["head"]["sha"], B)
        self.assertEqual(observe_webhook(FIX["webhook"], "delayed")["reason"], "missing_common_occurrence")
        self.assertEqual(observe_timeline(42, 7, FIX["timeline"])["reason"], "missing_exact_event_revision")
        # A current ready state alone supplies no transition or historical SHA.
        self.assertTrue(FIX["current_pull"]["draft"] is False)
        self.assertNotIn("id", FIX["current_pull"])
        self.assertEqual(observe_snapshot(42, FIX["current_pull"], False)["reason"], "history_gap")
        self.assertEqual(observe_snapshot(42, FIX["current_pull"], True)["reason"], "missing_transition")

    def test_conflict_and_fanout(self):
        r = Reconciler()
        first = r.bind_test_assertion("p1", 42, 7, 101, A)
        self.assertEqual(r.bind_test_assertion("p1", 42, 7, 101, B)["status"], "quarantined")
        self.assertEqual(r.bind_test_assertion("p1", 42, 7, 101, A)["status"], "quarantined")
        other = r.bind_test_assertion("p2", 42, 7, 101, A)
        self.assertEqual(other["status"], "resolved")
        self.assertIn(first["normalizedKey"], r.intents)
        self.assertEqual(len(r.intents), 2)

    def test_invalid_fails_closed(self):
        r = Reconciler()
        for args in [("p|x",42,7,101,A), ("p",42,7,True,A), ("p",42,7,101,B[:-1])]:
            with self.assertRaises(ValueError): r.bind_test_assertion(*args)
        bad = copy.deepcopy(FIX["webhook"]); bad["pull_request"]["number"] = 8
        with self.assertRaises(ValueError): observe_webhook(bad, "d")
        for bad_number in (True, 7.0, 0, 8):
            bad = copy.deepcopy(FIX["webhook"])
            bad["pull_request"]["number"] = bad_number
            with self.assertRaises(ValueError): observe_webhook(bad, "d")
        matching_one = copy.deepcopy(FIX["webhook"])
        matching_one["number"] = 1
        matching_one["pull_request"]["number"] = 1
        self.assertEqual(observe_webhook(matching_one, "d")["status"], "unresolved")
        for bad_number in (True, 1.0):
            matching_one["pull_request"]["number"] = bad_number
            with self.assertRaises(ValueError): observe_webhook(matching_one, "d")
        for bad_token in (" ", "", "x" * 129, "x|y"):
            with self.assertRaises(ValueError): observe_webhook(FIX["webhook"], bad_token)
            with self.assertRaises(ValueError): r.bind_test_assertion(bad_token, 42, 7, 101, A)
        self.assertFalse(r.intents)


if __name__ == "__main__":
    unittest.main(verbosity=2)
