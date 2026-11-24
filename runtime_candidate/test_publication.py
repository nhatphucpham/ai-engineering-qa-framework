"""Local synthetic publication/storage checks. No shared DB, engine or network."""
import copy
import hashlib
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

from qa_core.application import stage_report_package

from runtime_candidate import blobs
from runtime_candidate.blobs import BlobStore, descriptor
from runtime_candidate.common import Error, canonical, digest
from runtime_candidate.publication import prepare


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples' / 'reports' / 'runtime-v1' / 'failed-pending'


def inputs():
    return [json.loads((FIXTURE / (name + '.json')).read_text(encoding='utf-8'))
            for name in ('bundle', 'assessment')]


def anchors(bundle, assessment):
    return dict(expected_bundle_digest=digest(bundle), expected_assessment_digest=digest(assessment),
                run_id='run', report_id='runtime-report')


class PublicationTests(unittest.TestCase):
    def test_preserves_mixed_verdict_and_actions_with_private_lineage(self):
        bundle, assessment = inputs()
        # Remove a positive observation. A separate, valid violation remains.
        assessment['bindings'] = [row for row in assessment['bindings'] if row['relation'] == 'violates']
        prepared = prepare(bundle, assessment, **anchors(bundle, assessment))
        view = prepared.view
        self.assertEqual(view['verification'], 'failed')
        self.assertTrue(view['hasOpenMandatoryCoverage'])
        criterion, = view['criteria']
        self.assertEqual(criterion['status'], 'failed')
        self.assertTrue(criterion['hasOpenCoverage'])
        self.assertIn('CURRENT_BEHAVIOR_VIOLATION', criterion['reasonCodes'])
        self.assertEqual(view['humanDecision'], 'pending')
        self.assertEqual(view['legacyProjection']['status'], 'projection_unsupported')
        self.assertEqual([a['ownerRole'] for a in view['actions']], ['developer', 'qa', 'constraint-review-owner'])
        self.assertEqual(view['pendingConstraintIds'], [view['actions'][-1]['constraintIds'][0]])
        evidence_id, = criterion['evidenceIds']
        self.assertEqual(prepared.lineage['evidence'][evidence_id], 'ev-qc')
        self.assertEqual(prepared.lineage['criteria'][criterion['criterionId']], 'AC-1')
        self.assertEqual(view['sources'], [{'id': evidence_id, 'classification': 'derived_evidence_metadata',
                                            'level': 'integration', 'outcome': 'fail', 'provenanceKind': 'execution',
                                            'candidateRevisionMatch': True}])
        self.assertEqual(json.loads(prepared.view_bytes), view)
        self.assertEqual(json.loads(prepared.private_bytes), prepared.package)
        for raw, ref in [(prepared.private_bytes, prepared.private_ref), (prepared.view_bytes, prepared.view_ref)]:
            self.assertEqual(ref, {'sha256': hashlib.sha256(raw).hexdigest(), 'byteLength': len(raw)})

    def test_cross_project_and_tainted_inputs_remain_private_even_in_valid_identifiers(self):
        bundle, assessment = inputs()
        canary = 'SyntheticCredentialCanary'
        other_project = copy.deepcopy(bundle['projects'][0])
        other_project.update(id='other-project', checks=[])
        bundle['projects'].append(other_project)
        bundle['tasks'].append({'id': 'other-task', 'projectId': 'other-project',
                                'title': 'cross-project-canary', 'externalRef': None})
        # A schema-valid ID can carry private text. Make the target role, narrative,
        # evidence and criterion references all carry the same private canary.
        assessment['risk']['rationale'] = canary + ' untrusted narrative'
        handoff = bundle['handoffs'][0]
        handoff['criteria'][0].update(ownerRole=canary, clarification='ambiguous')
        def rename(raw):
            return json.loads(canonical(raw).replace(b'"AC-1"', ('"' + canary + '-AC"').encode())
                              .replace(b'"ev-qc"', ('"' + canary + '-evidence"').encode()))
        bundle, assessment = rename(bundle), rename(assessment)
        prepared = prepare(bundle, assessment, **anchors(bundle, assessment))
        for private in [canary.encode(), b'cross-project-canary', b'other-project', b'other-task',
                        b'qa/checks.json', b'candidate-r12', b'scopeDescription']:
            self.assertIn(private, prepared.private_bytes)
            self.assertNotIn(private, prepared.view_bytes)
        self.assertEqual(prepared.view['criteria'][0]['status'], 'unverified')
        self.assertEqual(prepared.view['actions'][0]['ownerRole'], 'requirement-owner')

    def test_caller_anchors_reject_substitution_and_package_tamper(self):
        bundle, assessment = inputs()
        trusted = anchors(bundle, assessment)
        with self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
            prepare(bundle, {**assessment, 'specimenNotice': 'self-consistent new input'}, **trusted)
        changed = copy.deepcopy(bundle)
        changed['tasks'][0]['title'] = 'self-consistent new bundle'
        rewritten = stage_report_package(changed, assessment, run_id='run', report_id='runtime-report')
        tampered = copy.deepcopy(stage_report_package(bundle, assessment, run_id='run', report_id='runtime-report'))
        tampered['graph']['reportReference']['reportSha256'] = '0' * 64
        for package in [rewritten, tampered]:
            with self.subTest(), patch('runtime_candidate.publication.stage_report_package', return_value=package):
                with self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
                    prepare(bundle, assessment, **trusted)


class BlobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'owned'
        self.store = BlobStore.create(self.root, owner='owner')

    def test_reopen_byte_pins_and_ref_shape(self):
        for raw in (b'', bytes(range(256)) * 8):
            ref = self.store.put(raw)
            self.assertEqual(self.store.put(raw), ref)
            self.assertEqual(BlobStore(self.root, owner='owner').get(ref), raw)
        for bad in [{'sha256': '../' + ref['sha256'], 'byteLength': 0},
                    {**ref, 'byteLength': True}, {**ref, 'byteLength': ref['byteLength'] - 1},
                    {**ref, 'byteLength': blobs.MAX_BLOB_BYTES + 1}, {**ref, 'path': 'unused'}]:
            with self.subTest(ref=bad), self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
                self.store.get(bad)
        with self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
            self.store.put(b'x' * (blobs.MAX_BLOB_BYTES + 1))
        with self.assertRaises(Error):
            BlobStore(self.root, owner='other')
        with self.assertRaises(Error):
            BlobStore.create(self.root, owner='owner')

    def test_bytes_differ_after_put_and_marker_tamper(self):
        raw = b'collector bytes'
        ref = self.store.put(raw)
        final = self.root / ref['sha256']
        final.write_bytes(b'x' * len(raw))
        with self.assertRaises(Error):
            self.store.get(ref)
        with self.assertRaises(Error):
            self.store.put(raw)
        self.assertEqual(final.read_bytes(), b'x' * len(raw))
        (self.root / blobs.MARKER).write_bytes(b'unrelated directory')
        with self.assertRaises(Error):
            self.store.put(b'new')

    def test_cloned_marker_links_and_swapped_namespace(self):
        sibling = self.root.with_name('sibling')
        sibling.mkdir()
        (sibling / blobs.MARKER).write_bytes((self.root / blobs.MARKER).read_bytes())
        with self.assertRaises(Error):
            BlobStore(sibling, owner='owner')
        raw = b'bytes outside owned store'
        ref = descriptor(raw)
        target = sibling / 'outside'
        target.write_bytes(raw)
        os.link(target, self.root / ref['sha256'])
        with self.assertRaises(Error):
            self.store.get(ref)
        alias = self.root.with_name('directory-link')
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(self.root), str(alias))
        else:
            alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(Error):
            BlobStore(alias, owner='owner')
        with self.assertRaises(Error):
            BlobStore.create(alias / 'new', owner='owner')
        self.assertFalse((self.root / 'new').exists())
        self.root.rename(self.root.with_name('retired'))
        BlobStore.create(self.root, owner='owner')
        with self.assertRaises(Error):
            self.store.put(raw)

    def _child(self, code, *args):
        proc = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root), *args], cwd=ROOT,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        def finish():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=15)
        self.addCleanup(finish)
        return proc

    def _expect_signal(self, child, expected):
        messages = Queue()
        Thread(target=lambda: messages.put(child.stdout.readline()), daemon=True).start()
        self.assertEqual(messages.get(timeout=15).strip(), expected)

    def test_independent_process_race_never_replaces(self):
        code = """import sys
from pathlib import Path
from runtime_candidate.blobs import BlobStore
s = BlobStore(Path(sys.argv[1]), owner='owner')
print('ready', flush=True)
sys.stdin.readline()
print(s.put(b'x' * 150000)['sha256'], flush=True)
"""
        children = [self._child(code) for _ in range(4)]
        for child in children:
            self._expect_signal(child, 'ready')
        for child in children:
            child.stdin.write('go\n')
            child.stdin.flush()
        raw = b'x' * 150000
        ref = descriptor(raw)
        for child in children:
            out, err = child.communicate(timeout=20)
            self.assertEqual(child.returncode, 0, err)
            self.assertEqual(out.strip(), ref['sha256'])
        self.assertEqual(self.store.get(ref), raw)
        self.assertEqual({p.name for p in self.root.iterdir()}, {blobs.MARKER, ref['sha256']})

    def test_killed_writer_and_unrelated_stage_are_never_served(self):
        code = """import sys
from pathlib import Path
from runtime_candidate import blobs
store = blobs.BlobStore(Path(sys.argv[1]), owner='owner')
def interrupted(stream, raw):
    stream.write(raw[:3])
    stream.flush()
    print('partial', flush=True)
    sys.stdin.readline()
blobs._write = interrupted
store.put(b'whole value')
"""
        child = self._child(code)
        self._expect_signal(child, 'partial')
        raw = b'whole value'
        ref = descriptor(raw)
        with self.assertRaises(Error):
            self.store.get(ref)
        child.kill()
        child.communicate(timeout=15)
        stage, = self.root.glob('.stage-*')
        self.assertEqual(stage.read_bytes(), raw[:3])
        with self.assertRaises(Error):
            self.store.get({'sha256': stage.name, 'byteLength': 3})
        with self.assertRaises(Error):
            self.store.get(ref)
        with patch.object(blobs, '_write', side_effect=OSError('private detail')):
            with self.assertRaisesRegex(Error, '^E_INTEGRITY$'):
                self.store.put(b'another')
        self.assertEqual(list(self.root.glob('.stage-*')), [stage])
        self.assertEqual(self.store.put(raw), ref)
        self.assertEqual(self.store.get(ref), raw)
        self.assertTrue(stage.exists())


if __name__ == '__main__':
    unittest.main()
