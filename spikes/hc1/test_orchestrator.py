"""Authored transport/fault conformance using historical replay, never live reasoning."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import shutil
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spikes.hc1 import orchestrator as hc

OLD = hc.ROOT / 'docs/vf1-results/vf1-20261118-r1'
TRANSPORT = {'kind': 'authored-conformance', 'agentTask': 'scripted-replay', 'model': 'none', 'effort': 'none'}


class OrchestratorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'a'
        self.folder.mkdir()
        for name in ('execution.json', 'worker.stdout.json', 'host-request.json', 'anchors.json'):
            shutil.copyfile(OLD / 'a' / name, self.folder / name)
        hc.put(self.folder / 'hc1-run.json', {'version': 'hc1-run-1.0.0', 'label': 'a'})
        self.proposal = hc.read(OLD / 'a/host-response.json')
        self.now = hc.utc()

    def issue(self, seconds=1800):
        result = hc.offer(self.folder, TRANSPORT, seconds=seconds, now=self.now)
        self.ticket = result['dispatchDigest']
        return result

    def envelope(self, proposal=None):
        return {'version': hc.COMPLETION, 'dispatchDigest': self.ticket,
                'response': self.proposal if proposal is None else proposal}

    def test_missing_connector_and_offer_duplicate_do_not_invoke(self):
        self.assertEqual('waiting_connector', hc.drive(self.folder, TRANSPORT)['state'])
        self.assertFalse((self.folder / 'dispatch.json').exists())
        first = self.issue()
        again = hc.offer(self.folder, TRANSPORT, now=self.now + timedelta(seconds=10))
        self.assertEqual(first['dispatch'], again['dispatch'])
        self.assertEqual(first['dispatchDigest'], again['dispatchDigest'])
        self.assertFalse((self.folder / 'accepted').exists())

    def test_self_contained_response_contract_and_held_contract_digest(self):
        from jsonschema import Draft202012Validator
        issued = self.issue()
        contract = issued['responseContract']
        Draft202012Validator.check_schema(contract['schema'])
        Draft202012Validator(contract['schema']).validate(self.proposal)
        self.assertIn('Do not run commands/checks', contract['instructions'])
        self.assertEqual(hc.digest(contract), issued['dispatch']['responseContractDigest'])
        changed = deepcopy(contract)
        changed['instructions'] += '\nAuthored contract drift'
        with patch.object(hc, 'response_contract', return_value=changed):
            with self.assertRaisesRegex(hc.Rejected, 'Dispatch no longer binds'):
                hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)

    def test_cli_offer_survives_ascii_pipe_and_preserves_independent_ticket(self):
        root = Path(self.temp.name) / 'cli-root'
        folder = root / 'docs/hc1-results/test/a'
        shutil.copytree(self.folder, folder)
        for relative in ('schemas/qa-assessment-v2.schema.json', 'spikes/hc1/HOST-INSTRUCTIONS.md'):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hc.ROOT / relative, target)
        code = ("from pathlib import Path; from spikes.hc1 import orchestrator as hc; import sys; "
                "hc.ROOT=Path(sys.argv[1]); sys.argv=['hc1','offer','test','--label','a',"
                "'--agent-task','native-ascii-test']; hc.main()")
        env = dict(os.environ, PYTHONIOENCODING='ascii')
        tickets = []
        for _ in range(2):
            result = subprocess.run([sys.executable, '-B', '-c', code, str(root)], cwd=hc.ROOT, env=env,
                                    capture_output=True, text=True, encoding='ascii', timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(result.stdout)
            tickets.append(parsed['dispatchDigest'])
            self.assertEqual(parsed['request'], hc.read(folder / 'host-request.json'))
            self.assertEqual(parsed['dispatchDigest'], hc.digest(hc.read(folder / 'dispatch.json')))
        self.assertEqual(tickets[0], tickets[1])

    def test_callable_auto_core_view_and_exact_repeat_after_deadline(self):
        calls = []
        def connector(offer):
            calls.append(offer)
            offer['request']['runId'] = 'authored-mutation-inside-transport-copy'
            return self.proposal
        result = hc.drive(self.folder, TRANSPORT, connector)
        self.ticket = result['dispatchDigest']
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['state'], 'view_ready')
        view = hc.read(self.folder / 'accepted/view.json')
        self.assertEqual([x['status'] for x in view['criteria']], ['verified', 'failed', 'failed', 'verified'])
        self.assertEqual(view['humanDecision'], 'pending')
        self.assertTrue((self.folder / 'accepted/dashboard.html').is_file())
        existing = {p.name: p.read_bytes() for p in (self.folder / 'accepted').iterdir()}
        duplicate = hc.complete(self.folder, self.ticket, self.envelope(), now=self.now + timedelta(days=1))
        self.assertEqual(duplicate, result)
        self.assertEqual(existing, {p.name: p.read_bytes() for p in (self.folder / 'accepted').iterdir()})

    def test_sibling_response_even_with_right_envelope_rejects(self):
        self.issue()
        for response in (hc.read(OLD / 'b/host-response.json'), dict(self.proposal, jobDigest='f' * 64),
                         dict(self.proposal, runId='wrong-run'), dict(self.proposal, jobId='wrong-job')):
            with self.subTest(response=response['runId']), self.assertRaises(ValueError):
                hc.complete(self.folder, self.ticket, self.envelope(response), now=self.now)
        self.assertFalse((self.folder / 'accepted').exists())
        self.assertEqual(len(list((self.folder / 'submissions').iterdir())), 4)
        hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)

    def test_wrong_ticket_and_version_cannot_relabel_attempt(self):
        self.issue()
        for change in ({'version': 'hc1-completion-2.0.0'}, {'dispatchDigest': 'e' * 64}, {'approval': True}):
            with self.subTest(change=change), self.assertRaises(hc.Rejected):
                hc.complete(self.folder, self.ticket, dict(self.envelope(), **change), now=self.now)
        with self.assertRaises(hc.Rejected):
            hc.complete(self.folder, 'e' * 64, self.envelope(), now=self.now)
        self.assertFalse((self.folder / 'accepted').exists())

    def test_source_execution_revision_and_reference_tamper_rejected(self):
        self.issue()
        for name in ('host-request.json', 'execution.json'):
            original = (self.folder / name).read_bytes()
            changed = hc.read(self.folder / name)
            if name == 'host-request.json':
                changed['candidateRevision'] = 'other-head'
            else:
                changed['inputHashes']['case/head/api.py'] = 'a' * 64
            (self.folder / name).write_bytes(hc.encode(changed))
            with self.assertRaises((ValueError, RuntimeError)):
                hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
            (self.folder / name).write_bytes(original)
        wrong = deepcopy(self.proposal)
        wrong['bindings'][0]['evidenceId'] = 'never-offered'
        with self.assertRaises(ValueError):
            hc.complete(self.folder, self.ticket, self.envelope(wrong), now=self.now)
        self.assertFalse((self.folder / 'accepted').exists())

    def test_timeout_admission_and_commit_fence(self):
        self.issue(seconds=1)
        with self.assertRaisesRegex(hc.Rejected, 'expired'):
            hc.complete(self.folder, self.ticket, self.envelope(), now=self.now + timedelta(seconds=1))
        self.assertFalse((self.folder / 'accepted').exists())
        # Simulate elapsed core work; second clock read must fence publication.
        with patch.object(hc, 'utc', side_effect=[self.now, self.now + timedelta(seconds=2)]):
            with self.assertRaisesRegex(hc.Rejected, 'expired before publication'):
                hc.complete(self.folder, self.ticket, self.envelope())
        self.assertFalse((self.folder / 'accepted').exists())
        self.assertFalse(list(self.folder.glob('.publish-*')))

    def test_cancel_first_and_accept_first_serialize(self):
        self.issue()
        hc.cancel(self.folder, self.ticket, now=self.now)
        with self.assertRaisesRegex(hc.Rejected, 'cancelled'):
            hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        self.assertEqual(hc.cancel(self.folder, self.ticket, now=self.now)['state'], 'cancelled')
        (self.folder / 'cancel.json').unlink()  # authored test reset only
        hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        with self.assertRaisesRegex(hc.Rejected, 'cannot be cancelled'):
            hc.cancel(self.folder, self.ticket, now=self.now)

    def test_transport_exception_and_duplicate_drive_never_reinvoke(self):
        calls = []
        def uncertain(_):
            calls.append(1)
            raise RuntimeError('authored transport disconnect after possible invocation')
        with self.assertRaisesRegex(RuntimeError, 'disconnect'):
            hc.drive(self.folder, TRANSPORT, uncertain)
        result = hc.drive(self.folder, TRANSPORT, uncertain)
        self.assertEqual(calls, [1])
        self.assertEqual(result['reason'], 'dispatch_already_issued')
        self.assertFalse((self.folder / 'accepted').exists())

    def test_preexisting_dispatch_without_invocation_marker_never_replays(self):
        self.issue()
        calls = []
        result = hc.drive(self.folder, TRANSPORT, lambda issued: calls.append(issued))
        self.assertEqual(result['reason'], 'dispatch_already_issued')
        self.assertEqual(calls, [])
        self.assertFalse((self.folder / 'invocation.json').exists())

    def test_lock_and_publish_interruption_do_not_claim_success(self):
        self.issue()
        with hc.locked(self.folder):
            with self.assertRaisesRegex(hc.Rejected, 'Concurrent mutation'):
                hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        with patch.object(Path, 'rename', side_effect=OSError('authored publication interruption')):
            with self.assertRaises(OSError):
                hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        self.assertEqual(hc.state(self.folder, self.ticket, now=self.now), 'waiting_response')
        self.assertFalse((self.folder / 'accepted').exists())
        hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)

    def test_conflicting_repeat_and_corrupt_published_file_rejected(self):
        self.issue()
        hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        changed = deepcopy(self.proposal)
        changed['risk']['rationale'] += ' authored conflicting update'
        with self.assertRaisesRegex(hc.Rejected, 'Conflicting duplicate'):
            hc.complete(self.folder, self.ticket, self.envelope(changed), now=self.now)
        (self.folder / 'accepted/dashboard.html').write_bytes(b'authored corruption')
        with self.assertRaisesRegex(hc.Rejected, 'bytes changed'):
            hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)

    def test_strict_json(self):
        path = self.folder / 'bad.json'
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            path.write_bytes(raw)
            with self.assertRaises(hc.Rejected):
                hc.read(path)

    def test_receipt_metadata_and_self_consistent_hash_tamper_rejected(self):
        self.issue()
        hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)
        path = self.folder / 'accepted/receipt.json'
        original = path.read_bytes()
        for key, value in [('humanDecision', 'approved'), ('runId', 'wrong-run'), ('state', 'completed'),
                           ('producerVersion', 'unknown'), ('extra', True)]:
            changed = hc.read(path)
            changed[key] = value
            path.write_bytes(hc.encode(changed))
            for call in (lambda: hc.state(self.folder, self.ticket, now=self.now),
                         lambda: hc.complete(self.folder, self.ticket, self.envelope(), now=self.now)):
                with self.subTest(field=key), self.assertRaisesRegex(hc.Rejected, 'receipt bytes changed'):
                    call()
            path.write_bytes(original)
        # Even changing a view and refreshing its receipt hash cannot forge a core decision.
        view_path = self.folder / 'accepted/view.json'
        view = hc.read(view_path)
        view['humanDecision'] = 'approved'
        view_path.write_bytes(hc.encode(view))
        changed = hc.read(path)
        changed['files']['view.json'] = hc.vf.sha(view_path)
        path.write_bytes(hc.encode(changed))
        with self.assertRaisesRegex(hc.Rejected, 'output bytes changed'):
            hc.state(self.folder, self.ticket, now=self.now)


if __name__ == '__main__':
    unittest.main()
