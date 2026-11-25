"""Behavioral O01–O17 oracles; authored fixture transport, not provider reasoning."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from . import anthropic_port, openai_port
from .common import LIMIT, PROFILES, Rejected, canonical, digest, parse, sha, validate_result
from .contracts import timestamp
from .corpus import DEADLINE, NOW, ROOT, event, make
from .harness import Harness, PORTS


def refresh(fixture):
    offer = fixture['offer']
    fixture['scope'] = {'projectId': offer['target']['projectId'], 'port': offer['port'],
        'sourceManifest': deepcopy(offer['sourceManifest']),
        'expectedBundleDigest': digest(fixture['expectedBundle']), 'omittedCheckIds': ['Baseline.test_api_page_and_size']}
    offer['policyPin']['scopeDigest'] = digest(fixture['scope'])
    offer['policyPin']['capabilityDigest'] = digest(fixture['capability'])


def wire(fixture, mutate):
    value = event(fixture)
    data = parse(value['body'])
    mutate(data)
    value['body'] = canonical(data)
    return value


class OfflineCases(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='qa-rc1-offline-')
        self.addCleanup(self.temp.cleanup)
        self.counter = 0
        self.traces = []
        self.assertionCalls = 0

    def assertEqual(self, *args, **kwargs):
        self.assertionCalls += 1
        return super().assertEqual(*args, **kwargs)

    def assertTrue(self, *args, **kwargs):
        self.assertionCalls += 1
        return super().assertTrue(*args, **kwargs)

    def setup_fixture(self, fixture=None, delivery=None, *, capacity=(400, 400), no_delivery=False):
        f = fixture or make(self.port)
        self.counter += 1
        h = Harness(Path(self.temp.name) / str(self.counter), create=True)
        self.register(h, f, capacity=capacity)
        if not no_delivery:
            h.register_delivery('delivery', f['offer'], delivery if delivery is not None else event(f))
        return h, f

    def register(self, h, f, *, capacity=(400, 400)):
        h.register(f['offer'], f['sources'], f['capability'], expected_bundle_digest=digest(f['expectedBundle']),
                   omitted_check_ids=['Baseline.test_api_page_and_size'], capacity=capacity, scope=f['scope'])

    def trace(self, label, h, f, value=None, *, clock=NOW, before=None, submitted_offer=None, submitted_raw=None):
        state = h.inspect()
        attempt = state['attempts'][f['offer']['attemptId']]
        deliveries = state['deliveries']
        delivery = deliveries.get(attempt.get('deliveryId') or attempt.get('expectedDeliveryId'))
        if delivery is None:
            delivery = next((d for d in deliveries.values() if d['offerDigest'] == digest(f['offer'])), None)
        from .harness import materialize
        body = materialize(delivery['event'])['body'] if delivery else None
        self.traces.append({'scenario': label, 'offerDigest': digest(f['offer']),
            'jobDigest': f['offer']['jobDigest'], 'contextSourcePins': f['offer']['sourceManifest'],
            'responseContractDigest': f['offer']['responseContractDigest'], 'policyPin': f['offer']['policyPin'],
            'target': f['offer']['target'], 'budget': f['offer']['budget'], 'clock': clock,
            'submittedOfferSha256': (sha(submitted_raw) if submitted_raw is not None else
                                    digest(submitted_offer) if submitted_offer is not None else None),
            'fixtureSha256': sha(body) if body is not None else None, 'profileSource': f['profileSource'],
            'calls': attempt['calls'], 'releasedBytes': attempt['releasedBytes'],
            'requestSha256': attempt.get('requestDigest'), 'reservation': attempt['reservation'],
            'reconciled': attempt['reconciled'], 'usage': attempt.get('usage'),
            'intentOpen': attempt['intentOpen'],
            'history': attempt['history'], 'account': state['accounts'][attempt['account']],
            'receiptSha256': attempt.get('receiptDigest'), 'actual': value,
            'applicationEffects': state['applicationEffects'],
            'before': None if before is None else {'accounts': before['accounts'],
                'attempts': {k: {key: a[key] for key in ('state', 'calls', 'releasedBytes', 'reservation', 'history')}
                             for k, a in before['attempts'].items()}}})
        self.assertEqual(0, state['applicationEffects'])
        self.assertTrue(attempt['calls'] <= 1)

    def denied(self, code, action, label, h, f, *, clock=NOW, submitted_offer=None, submitted_raw=None):
        before = h.inspect()
        try:
            action()
        except Rejected as exc:
            self.assertEqual(code, exc.code)
            after = h.inspect()
            self.assertEqual({k: (a['calls'], a['releasedBytes']) for k, a in before['attempts'].items()},
                             {k: (a['calls'], a['releasedBytes']) for k, a in after['attempts'].items()})
            self.trace(label, h, f, {'denied': exc.code}, before=before, clock=clock,
                       submitted_offer=submitted_offer, submitted_raw=submitted_raw)
        else:
            self.fail('Expected ' + code + ': ' + label)

    def start(self, h, f):
        admitted = h.admit(canonical(f['offer']), now=NOW)
        h.emit(f['offer'], admitted['handle'], now=NOW)
        return admitted['handle']

    def run_event(self, f=None, delivery=None, *, now=NOW, validation_now=None, status=None, diagnostic=None):
        h, f = self.setup_fixture(f, delivery)
        before = h.inspect()
        handle = self.start(h, f)
        receipt = h.receive(f['offer'], handle, 'delivery', now=now, validation_now=validation_now)
        if status:
            self.assertEqual(status, receipt['state'])
        if diagnostic:
            self.assertEqual(diagnostic, receipt['result']['diagnostic'])
        validate_result(receipt['result'], f['offer'], (delivery if delivery is not None else event(f))['body'])
        self.trace('receive ' + str(status), h, f, {'state': receipt['state'],
            'outcome': receipt['result']['outcome'], 'diagnostic': receipt['result']['diagnostic'],
            'validation': receipt['validation']}, before=before,
            clock={'receive': now, 'validation': validation_now if validation_now is not None else now},
            submitted_raw=canonical(f['offer']))
        return h, f, receipt

    def O01(self):
        h, f, receipt = self.run_event(status='candidate_validated')
        self.assertEqual(['verified', 'failed', 'failed', 'unverified'], receipt['validation']['statuses'])
        self.assertEqual('failed', receipt['validation']['verification'])
        self.assertEqual('pending', receipt['validation']['humanDecision'])
        self.assertTrue(receipt['validation']['hasUnverifiedMandatory'])
        self.assertEqual(digest(f['expectedBundle']), receipt['validation']['bundleDigest'])
        request = parse(bytes.fromhex(h.inspect()['attempts'][f['offer']['attemptId']]['requestHex']))
        if self.port == 'local_host':
            context = request['context']
            self.assertEqual({'kind', 'context'}, set(request))
        elif self.port == 'openai':
            context = parse(request['input'][0]['content'][0]['text'].encode())
            self.assertEqual([], request['tools'])
            self.assertEqual('disabled', request['truncation'])
        else:
            context = parse(request['messages'][0]['content'][0]['text'].encode())
            self.assertEqual({'model', 'stream', 'max_tokens', 'messages'}, set(request))
        self.assertEqual({'job': f['offer']['job'], 'responseContract': f['offer']['responseContract']}, context)
        self.assertEqual(1, h.inspect()['attempts']['attemptA']['calls'])
        changed = deepcopy(f['proposal'])
        removed = changed['bindings'].pop()
        changed['evidenceReviews'] = [r for r in changed['evidenceReviews'] if r['evidenceId'] != removed['evidenceId']]
        self.run_event(f, event(f, proposal=changed), status='malformed')

    def O02(self):
        h, f = self.setup_fixture()
        changes = [('target', k) for k in f['offer']['target']] + [(None, k) for k in
            ('assignment', 'fence', 'effectNonce', 'executionDigest', 'jobDigest', 'responseContractDigest')]
        for section, key in changes:
            bad = deepcopy(f['offer'])
            obj = bad[section] if section else bad
            obj[key] = obj[key] + 1 if type(obj[key]) is int else ('a' * 64 if key.endswith('Digest') else
                       '3' * 32 if key in ('assignment', 'effectNonce') else obj[key] + 'x')
            if key == 'projectConfigVersion': bad['policyPin']['configVersion'] = obj[key]
            if key == 'dataPolicyVersion': bad['policyPin']['policyVersion'] = obj[key]
            try:
                h.admit(canonical(bad), now=NOW)
            except Rejected as exc:
                self.assertTrue(exc.code in ('E_INPUT', 'E_INTEGRITY', 'E_CONFLICT', 'E_VF1_SCOPE', 'E_VF1_JOB_DIGEST'))
                denied_code = exc.code
            else:
                self.fail('held target changed: ' + key)
            self.assertEqual(0, h.inspect()['attempts']['attemptA']['calls'])
            self.trace('held mismatch ' + str(section) + '/' + key, h, f, {'denied': denied_code}, submitted_offer=bad)
        sibling = make(self.port, attempt='attemptB')
        self.register(h, sibling)
        h.register_delivery('sibling', sibling['offer'], event(sibling))
        other_port = next(p for p in PROFILES if p != self.port)
        for other_fixture, did in [(make(other_port, attempt='attemptPort'), 'otherPort'),
                                   (make(self.port, attempt='attemptPolicy', config_version=2, policy_version=2), 'otherPolicy')]:
            self.register(h, other_fixture)
            h.register_delivery(did, other_fixture['offer'], event(other_fixture))
        other, _ = self.setup_fixture(sibling)
        other_ticket = other.admit(canonical(sibling['offer']), now=NOW)['handle']
        ticket = self.start(h, f)
        self.denied('E_CHANNEL', lambda: h.receive(f['offer'], other_ticket, 'delivery', now=NOW), 'foreign ticket same job', h, f)
        self.denied('E_CHANNEL', lambda: h.receive(f['offer'], ticket, 'sibling', now=NOW), 'sibling delivery same job', h, f)
        for did in ('otherPort', 'otherPolicy'):
            self.denied('E_CHANNEL', lambda did=did: h.receive(f['offer'], ticket, did, now=NOW), 'same job foreign ' + did, h, f)
        good = h.receive(f['offer'], ticket, 'delivery', now=NOW)
        self.assertEqual('candidate_validated', good['state'])
        self.trace('correct channel identical authored bytes', h, f, {'state': good['state']})
        for anchor in ('runId', 'jobId', 'jobDigest'):
            candidate = deepcopy(f['proposal']); candidate[anchor] = 'foreign'
            self.run_event(f, event(f, proposal=candidate), status='malformed')
        candidate = deepcopy(f['proposal']); candidate['evidenceReviews'][0]['evidenceId'] = 'foreign-evidence'
        self.run_event(f, event(f, proposal=candidate), status='malformed')

    def O03(self):
        h, f = self.setup_fixture()
        for raw in (b'{"version":1,"version":2}', b'{"a":NaN}', b'{"a":Infinity}', b'\xff', b'[]'):
            self.denied('E_INPUT', lambda raw=raw: h.admit(raw, now=NOW), 'strict JSON ' + sha(raw), h, f, submitted_raw=raw)
        variants = []
        for key, value in [('version', 'unknown'), ('profile', 'unknown'), ('fence', True), ('assignment', 'bad'),
                           ('deadlineUtc', '2026-02-30T00:00:00Z'), ('jobDigest', 'ABC')]:
            bad = deepcopy(f); bad['offer'][key] = value; variants.append((key, bad))
        bad = deepcopy(f); bad['offer']['authorized'] = True; variants.append(('extra authority', bad))
        bad = deepcopy(f); bad['offer']['target']['handoffId'] = None; variants.append(('target type', bad))
        for label, change in [('contract version', lambda c: c.update(version='unknown')),
                              ('numeric boolean schema', lambda c: c['schema'].update(additionalProperties=0)),
                              ('foreign schema reference', lambda c: c['schema'].update({'$ref': 'https://invalid.example/schema'}))]:
            bad = deepcopy(f); change(bad['offer']['responseContract'])
            bad['offer']['responseContractDigest'] = digest(bad['offer']['responseContract'])
            variants.append((label, bad))
        bad = deepcopy(f); bad['offer']['sourceManifest'].append(deepcopy(bad['offer']['sourceManifest'][0])); variants.append(('duplicate source', bad))
        for label, bad in variants:
            bh, _ = self.setup_fixture(bad)
            try: bh.admit(canonical(bad['offer']), now=NOW)
            except Rejected: pass
            else: self.fail(label)
            self.trace(label, bh, bad)
        self.run_event(status='candidate_validated')  # Digit-leading UUIDs and inert known relative paths.
        unicode_fixture = make(self.port, risk_rationale='Dữ liệu\x00e\u0301')
        _, _, result = self.run_event(unicode_fixture, event(unicode_fixture), status='candidate_validated')
        self.assertEqual('Dữ liệu\x00e\u0301', result['result']['proposal']['risk']['rationale'])
        self.assertTrue(digest('é') != digest('e\u0301'))

    def O04(self):
        h, f = self.setup_fixture()
        raw = canonical(f['offer']); padded = raw + b' ' * (LIMIT - len(raw))
        ticket = h.admit(padded, now=NOW)['handle']
        self.trace('offer at64KiB', h, f, submitted_raw=padded)
        self.denied('E_INPUT', lambda: h.admit(padded + b' ', now=NOW), 'offer above64KiB', h, f, submitted_raw=padded + b' ')
        for size, expected in ((LIMIT, 'candidate_validated'), (LIMIT + 1, 'malformed')):
            delivery = event(f); delivery['body'] += b' ' * (size - len(delivery['body']))
            self.run_event(f, delivery, status=expected)
        for count in (64, 65):
            extra = deepcopy(f)
            for i in range(count - len(extra['offer']['sourceManifest'])):
                aid = f'extra{i}'
                extra['sources'][aid] = {'hex': '', 'classification': 'safe_source', 'revision': 'v1', 'lineageIds': []}
                extra['offer']['sourceManifest'].append({'artifactId': aid, 'revision': 'v1', 'sha256': sha(b''),
                                                       'bytes': 0, 'lineageIds': [], 'classification': 'safe'})
            refresh(extra)
            eh, _ = self.setup_fixture(extra)
            if count == 64:
                eh.admit(canonical(extra['offer']), now=NOW)
            else:
                self.denied('E_INPUT', lambda: eh.admit(canonical(extra['offer']), now=NOW), 'source count65', eh, extra)
            self.trace('source count ' + str(count), eh, extra)
        for usage in ((100, 100), (101, 100), (100, 101)):
            self.run_event(f, event(f, usage=usage), status='candidate_validated' if usage == (100, 100) else 'blocked_budget')
        for field, value in [('maxInvocations', 2), ('maxSubmissions', 2), ('maxResponseBytes', LIMIT + 1),
                             ('inputTokenBound', 0), ('maxOutputTokens', 0)]:
            bad = deepcopy(f); bad['offer']['budget'][field] = value
            bh, _ = self.setup_fixture(bad)
            self.denied('E_BUDGET', lambda: bh.admit(canonical(bad['offer']), now=NOW), field, bh, bad)

    def O05(self):
        f = make(self.port)
        for classification in ('restricted', 'secret_tainted'):
            bad = deepcopy(f)
            bad['sources']['artifact-1']['classification'] = classification
            # A trusted manifest claiming safe cannot hide its denied ancestor.
            h, _ = self.setup_fixture(bad)
            self.denied('E_POLICY', lambda: h.admit(canonical(bad['offer']), now=NOW), 'denied ancestor ' + classification, h, bad)
        for parent in ('unknownSource', 'contextRecord'):
            bad = deepcopy(f)
            bad['sources']['contextRecord']['lineageIds'] = sorted(set(bad['sources']['contextRecord']['lineageIds'] + [parent]))
            for r in bad['offer']['sourceManifest']:
                if r['artifactId'] == 'contextRecord': r['lineageIds'] = sorted(set(bad['sources']['contextRecord']['lineageIds']))
            refresh(bad); h, _ = self.setup_fixture(bad)
            self.denied('E_POLICY', lambda: h.admit(canonical(bad['offer']), now=NOW), 'unknown/cyclic lineage ' + parent, h, bad)
        hidden = deepcopy(f); hidden['offer']['job']['workspaceHistory'] = 'hidden'
        hidden['offer']['jobDigest'] = digest(hidden['offer']['job'])
        h, _ = self.setup_fixture(hidden)
        try: h.admit(canonical(hidden['offer']), now=NOW)
        except Rejected: pass
        else: self.fail('unknown job fields')
        self.trace('no hidden history', h, hidden)
        # Actual pinned restricted historical input, read-only negative only. No rerun or relabel.
        from runtime_candidate.fixture_import import load_hc1
        archived = load_hc1('b')
        restricted = archived['sources']['vf1-coverage-policy']
        self.assertEqual('restricted', restricted[1])
        raw = restricted[0]
        bad = deepcopy(f)
        bad['sources']['contextRecord']['hex'] = raw.hex()
        bad['sources']['contextRecord']['classification'] = restricted[1]
        bad['sources']['contextRecord']['revision'] = restricted[2]
        row = next(r for r in bad['offer']['sourceManifest'] if r['artifactId'] == 'contextRecord')
        row.update(sha256=sha(raw), bytes=len(raw), classification='restricted', revision=restricted[2])
        refresh(bad); h, _ = self.setup_fixture(bad)
        self.denied('E_POLICY', lambda: h.admit(canonical(bad['offer']), now=NOW),
                    'actual immutable HC1 restricted host request sha=' + sha(raw), h, bad)
        self.assertEqual(archived['provenance']['originalFileDigests'][archived['provenance']['origin'] + '/host-request.json'], sha(raw))
        missing = deepcopy(f)
        del missing['sources']['contextRecord']
        missing['offer']['sourceManifest'] = [r for r in missing['offer']['sourceManifest'] if r['artifactId'] != 'contextRecord']
        refresh(missing); h, _ = self.setup_fixture(missing)
        self.denied('E_POLICY', lambda: h.admit(canonical(missing['offer']), now=NOW), 'missing required issuer context record', h, missing)
        self.O01()  # Also assert actual released context equals only the approved job+contract.

    def O06(self):
        f = make(self.port)
        for key in ('enrolled', 'isolatedContext', 'noTools', 'noOutbound'):
            bad = deepcopy(f); bad['capability'][key] = False; refresh(bad)
            h, _ = self.setup_fixture(bad)
            self.denied('E_CAPABILITY', lambda: h.admit(canonical(bad['offer']), now=NOW), 'missing control ' + key, h, bad)
        for key in ('requireModelEcho', 'modelSelector', 'enrollmentSelector'):
            bad = deepcopy(f); bad['capability'].pop(key); refresh(bad)
            h, _ = self.setup_fixture(bad)
            self.denied('E_CAPABILITY', lambda: h.admit(canonical(bad['offer']), now=NOW), 'absent capability field ' + key, h, bad)
        for change in ({'enabled': False}, {'enrolled': False}, {'ports': []}, {'configVersion': 2}, {'sourceIds': []}):
            h, _ = self.setup_fixture(f); admitted = h.admit(canonical(f['offer']), now=NOW)
            h.authority(f['offer'], **change)
            code = 'E_CAPABILITY' if change == {'enrolled': False} else 'E_POLICY'
            self.denied(code, lambda: h.emit(f['offer'], admitted['handle'], now=NOW), 'revoke before release ' + str(change), h, f)
            self.assertEqual(0, h.inspect()['attempts']['attemptA']['calls'])
        h, _ = self.setup_fixture(f, no_delivery=True)
        self.denied('E_CAPABILITY', lambda: h.admit(canonical(f['offer']), now=NOW), 'missing enrolled fixture connector', h, f)
        if self.port != 'local_host':
            bad = deepcopy(f); bad['capability']['requireModelEcho'] = False; refresh(bad)
            h, _ = self.setup_fixture(bad)
            self.denied('E_CAPABILITY', lambda: h.admit(canonical(bad['offer']), now=NOW), 'API cannot disable model echo', h, bad)

    def O07(self):
        h, f = self.setup_fixture(capacity=(100, 100))
        first = h.admit(canonical(f['offer']), now=NOW)
        before = h.inspect()
        repeated = h.admit(canonical(f['offer']), now=NOW)
        self.assertEqual('unresolved_send', repeated['state'])
        self.assertEqual(before, h.inspect())
        h.emit(f['offer'], first['handle'], now=NOW)
        self.denied('E_CONFLICT', lambda: h.emit(f['offer'], first['handle'], now=NOW), 'duplicate emission', h, f)
        changed = deepcopy(f['offer']); changed['deadlineUtc'] = '2026-11-25T00:03:00Z'
        self.denied('E_CONFLICT', lambda: h.admit(canonical(changed), now=NOW), 'same attempt different digest', h, f)
        h, f = self.setup_fixture(capacity=(100, 100))
        sibling = make(self.port, attempt='attemptB'); self.register(h, sibling)
        h.register_delivery('sibling', sibling['offer'], event(sibling))
        barrier = threading.Barrier(2)
        def race(item):
            barrier.wait()
            try: return item, h.admit(canonical(item['offer']), now=NOW)
            except Rejected as exc: return item, {'denied': exc.code}
        with ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(race, (f, sibling)))
        self.assertEqual(['E_BUDGET'], [out['denied'] for _, out in outcomes if 'denied' in out])
        winner, admitted = next((item, out) for item, out in outcomes if 'handle' in out)
        h.emit(winner['offer'], admitted['handle'], now=NOW)
        self.assertEqual(1, sum(a['calls'] for a in h.inspect()['attempts'].values()))
        self.trace('different attempts one shared allocation race', h, winner, {'loser': 'blocked_budget'})
        # Same-ID conflict remains when there is enough capacity for two reservations.
        h, f = self.setup_fixture(capacity=(500, 500))
        h.admit(canonical(f['offer']), now=NOW)
        changed = deepcopy(f['offer']); changed['deadlineUtc'] = '2026-11-25T00:03:00Z'
        self.denied('E_CONFLICT', lambda: h.admit(canonical(changed), now=NOW), 'same ID enough balance', h, f)
        for field in ('inputTokenBound', 'maxOutputTokens'):
            bad = make(self.port); bad['offer']['budget'][field] = None
            bh, _ = self.setup_fixture(bad)
            self.denied('E_BUDGET', lambda: bh.admit(canonical(bad['offer']), now=NOW), 'unreliable bound ' + field, bh, bad)

    def O08(self):
        deadline = timestamp(DEADLINE)
        for now in (deadline, deadline + 1):
            h, f = self.setup_fixture()
            self.assertEqual('expired_fenced', h.admit(canonical(f['offer']), now=now)['state'])
            self.assertEqual(0, h.inspect()['attempts']['attemptA']['calls'])
            self.trace('deadline admission ' + str(now), h, f, clock=now)
        h, f = self.setup_fixture(); ticket = h.admit(canonical(f['offer']), now=NOW)['handle']
        self.assertEqual('expired_fenced', h.emit(f['offer'], ticket, now=deadline)['state'])
        self.assertEqual(0, h.inspect()['attempts']['attemptA']['calls'])
        self.trace('expiry between intent/emission', h, f, clock=deadline)
        for mode in ('cancel', 'expire', 'expire_validation'):
            h, f = self.setup_fixture(); ticket = self.start(h, f)
            if mode == 'cancel': h.cancel(f['offer'])
            with patch('spikes.p4d_rc1.harness.validate_candidate', side_effect=AssertionError('core must not run')):
                r = h.receive(f['offer'], ticket, 'delivery', now=deadline if mode == 'expire' else NOW,
                              validation_now=deadline if mode == 'expire_validation' else None)
            self.assertEqual('cancelled_fenced' if mode == 'cancel' else 'expired_fenced', r['state'])
            self.assertEqual(None, r['validation'])
            self.assertEqual('unknown', r['remoteTermination'])
            self.trace(mode, h, f, {'state': r['state']}, clock={'receive': deadline if mode == 'expire' else NOW,
                       'validation': deadline if mode == 'expire_validation' else NOW})
        h, f, receipt = self.run_event(status='candidate_validated')
        self.denied('E_CONFLICT', lambda: h.cancel(f['offer']), 'validation first cancel rejected', h, f)

    def O09(self):
        for fault in ('before_intent', 'after_intent', 'after_emit'):
            h, f = self.setup_fixture()
            if fault in ('before_intent', 'after_intent'):
                self.denied('E_INJECTED_' + fault.upper(), lambda: h.admit(canonical(f['offer']), now=NOW, fault=fault), fault, h, f)
            else:
                self.start(h, f)
            (h.root / 'probe-offer.json').write_bytes(canonical(f['offer']))
            child = subprocess.run([sys.executable, '-B', '-m', 'spikes.p4d_rc1.reopen_probe', str(h.root)],
                                   cwd=ROOT, capture_output=True, timeout=20)
            self.assertEqual(0, child.returncode)
            observed = parse(child.stdout)
            self.assertTrue(observed['emit'] != 'unexpected_emit')
            reopened = Harness(h.root)
            if fault == 'before_intent':
                self.assertEqual('offered', observed['replay']['state'])
                ticket = reopened.admit(canonical(f['offer']), now=NOW)['handle']
                reopened.emit(f['offer'], ticket, now=NOW)
            else:
                self.assertEqual('unresolved_send', observed['replay']['state'])
                self.assertEqual([100, 100], observed['reservation'])
                held = h.inspect()['attempts']['attemptA']['handle']
                code = 'E_UNRESOLVED' if fault == 'after_intent' else 'E_CONFLICT'
                self.denied(code, lambda: reopened.emit(f['offer'], held, now=NOW), 'retained handle cannot resend', reopened, f)
                self.assertEqual(0 if fault == 'after_intent' else 1, reopened.inspect()['attempts']['attemptA']['calls'])
                # Cancellation or expiry changes acceptance state, never the independent
                # ambiguity/reservation fence of an orphaned send with no received result.
                reopened.cancel(f['offer'])
                sibling = make(self.port, attempt='attemptAfterOrphan'); self.register(reopened, sibling)
                reopened.register_delivery('afterOrphan', sibling['offer'], event(sibling))
                self.denied('E_UNRESOLVED', lambda: reopened.admit(canonical(sibling['offer']), now=NOW),
                            'cancelled orphan does not free funded account', reopened, sibling)
                self.assertEqual([100, 100], reopened.inspect()['attempts']['attemptA']['reservation'])
                self.assertTrue(reopened.inspect()['attempts']['attemptA']['intentOpen'])
            self.trace('actual new-process reopen ' + fault, reopened, f, observed)
        h, f = self.setup_fixture(); ticket = self.start(h, f)
        reopened = Harness(h.root)
        with patch('spikes.p4d_rc1.harness.validate_candidate', side_effect=AssertionError('late must not validate')):
            receipt = reopened.receive(f['offer'], ticket, 'delivery', now=NOW)
        self.assertEqual('unresolved_send', receipt['state'])
        self.trace('orphaned late response stays unresolved', reopened, f)

    def O10(self):
        h, f, receipt = self.run_event(status='candidate_validated')
        before = h.inspect()
        with patch('spikes.p4d_rc1.harness.validate_candidate', side_effect=AssertionError('no revalidation')):
            self.assertEqual(receipt, Harness(h.root).replay(f['offer']))
            self.assertEqual(receipt, h.admit(canonical(f['offer']), now=timestamp(DEADLINE) + 10))
        self.assertEqual(before, h.inspect())
        self.trace('completed historical exact replay after expiry', h, f, before=before, clock=timestamp(DEADLINE) + 10)
        h.authority(f['offer'], enabled=False)
        self.denied('E_POLICY', lambda: h.replay(f['offer']), 'replay current revoke', h, f)
        for damage in ('receipt', 'missing_receipt', 'delivery', 'request'):
            h, f, _ = self.run_event(status='candidate_validated')
            with h.unit(write=True) as state:
                a = state['attempts']['attemptA']
                if damage == 'receipt': a['receipt']['state'] = 'forged'
                elif damage == 'missing_receipt': a['receipt'] = None
                elif damage == 'delivery': state['deliveries']['delivery']['event']['body'] = {'hex': b'changed'.hex()}
                else: a['requestHex'] = b'changed'.hex()
            self.denied('E_UNRESOLVED', lambda: h.replay(f['offer']), 'damaged ' + damage, h, f)
            before = h.inspect()
            self.denied('E_UNRESOLVED', lambda: h.reconcile(f['offer'], [12, 7], now=NOW), 'no refund from damaged ' + damage, h, f)
            self.assertEqual(before, h.inspect())
        h, f = self.setup_fixture(); (h.root / '.mutation-lock').mkdir()
        with self.assertRaises(Rejected) as caught: h.replay(f['offer'])
        self.assertEqual('E_UNRESOLVED', caught.exception.code)
        self.assertTrue((h.root / '.mutation-lock').is_dir())

    def O11(self):
        f = make(self.port)
        if self.port == 'local_host':
            refusal = {'kind': 'refusal', 'body': canonical(f['proposal']), 'usageCounts': {'inputTokens': 12, 'outputTokens': 7}}
            incomplete = {'kind': 'output_limit', 'body': canonical(f['proposal']), 'usageCounts': None}
        elif self.port == 'openai':
            refusal = wire(f, lambda d: d['output'][0]['content'].append({'type': 'refusal', 'refusal': 'authored refusal'}))
            incomplete = wire(f, lambda d: d.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'}))
        else:
            refusal = wire(f, lambda d: d.update(stop_reason='refusal'))
            incomplete = wire(f, lambda d: d.update(stop_reason='max_tokens'))
        self.run_event(f, refusal, status='refused', diagnostic='refusal')
        self.run_event(f, incomplete, status='incomplete', diagnostic='output_limit')
        for proposal in ({}, {'version': 'unknown'}, dict(f['proposal'], authorized=True)):
            self.run_event(f, event(f, proposal=proposal), status='malformed')
        for raw in (b'', b'{', b'\xff', b'{"a":1,"a":2}'):
            delivery = event(f)
            if self.port == 'local_host': delivery['body'] = raw
            else:
                data = parse(delivery['body'])
                blocks = data['output'][0]['content'] if self.port == 'openai' else data['content']
                blocks[0]['text'] = raw.decode('utf-8', errors='replace')
                delivery['body'] = canonical(data)
            self.run_event(f, delivery, status='malformed')
        if self.port != 'local_host':
            for raw in (b'\xff', b'{"object":"response","object":"response"}'):
                delivery = event(f); delivery['body'] = raw
                self.run_event(f, delivery, status='malformed', diagnostic='parse')

    def O12(self):
        f = make(self.port)
        if self.port == 'local_host':
            variants = [(kind, code) for kind, code in [('auth_error', 'auth'), ('permission_error', 'permission'),
                        ('rate_limit', 'rate_limit'), ('service_error', 'service'), ('unavailable', 'unavailable')]]
            events = [({'kind': kind, 'body': None, 'usageCounts': None}, code) for kind, code in variants]
        else:
            variants = [(401, 'auth'), (403, 'permission'), (429, 'rate_limit'), (500, 'service')]
            if self.port == 'anthropic': variants += [(529, 'overload')]
            events = [({'kind': 'http', 'status': status, 'body': b'{"private":"do not log"}', 'requestId': 'authored'}, code)
                      for status, code in variants]
        for delivery, code in events:
            h, _, receipt = self.run_event(f, delivery, status='provider_error', diagnostic=code)
            self.assertTrue('private' not in str(receipt))
            self.assertEqual([100, 100], h.inspect()['attempts']['attemptA']['reservation'])
        for kind in ('timeout', 'transport_loss'):
            delivery = ({'kind': kind, 'body': None, 'usageCounts': None} if self.port == 'local_host'
                        else {'kind': kind, 'status': None, 'body': None, 'requestId': None})
            h, _, _ = self.run_event(f, delivery, status='unresolved_send', diagnostic=kind)
            self.assertEqual([100, 100], h.inspect()['attempts']['attemptA']['reservation'])

    def O13(self):
        f = make(self.port)
        variants = [({'object': 'message'}, 'malformed'), ({'status': None}, 'malformed'),
                    ({'status': 'in_progress'}, 'unsupported'), ({'error': {'code': 'authored'}}, 'provider_error')]
        for change, expected in variants:
            self.run_event(f, wire(f, lambda d, change=change: d.update(change)), status=expected)
        for key in ('type', 'role', 'status'):
            def mutate(d, key=key): d['output'][0][key] = 'incomplete' if key == 'status' else 'user'
            self.run_event(f, wire(f, mutate), status='incomplete' if key == 'status' else 'malformed')
        for mutate, expected in [
            (lambda d: d.pop('status'), 'malformed'),
            (lambda d: d.update(status='failed', output=[]), 'provider_error'),
            (lambda d: (d.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'}), d.pop('output')), 'incomplete'),
            (lambda d: d['output'].append({'type': 'tool_call'}), 'unsupported'),
            (lambda d: d['output'].append(deepcopy(d['output'][0])), 'malformed'),
            (lambda d: d['output'][0]['content'].append({'type': 'output_text', 'text': '{}'}), 'malformed')]:
            self.run_event(f, wire(f, mutate), status=expected)
        self.run_event(f, wire(f, lambda d: d['output'].insert(0, {'type': 'reasoning', 'summary': []})), status='candidate_validated')

    def O14(self):
        f = make(self.port)
        for key, value in [('type', 'response'), ('role', 'user'), ('stop_reason', None), ('content', [])]:
            self.run_event(f, wire(f, lambda d, key=key, value=value: d.update({key: value})), status='malformed')
        self.run_event(f, wire(f, lambda d: d.pop('stop_reason')), status='malformed')
        for stop, expected in [('refusal', 'refused'), ('max_tokens', 'incomplete'),
                               ('model_context_window_exceeded', 'incomplete'), ('tool_use', 'unsupported'),
                               ('pause_turn', 'unsupported'), ('stop_sequence', 'unsupported'), ('unknown', 'unsupported')]:
            self.run_event(f, wire(f, lambda d, stop=stop: d.update(stop_reason=stop)), status=expected)
        self.run_event(f, wire(f, lambda d: d['content'].append({'type': 'thinking', 'thinking': 'private'})), status='unsupported')
        self.run_event(f, wire(f, lambda d: d['content'].append(deepcopy(d['content'][0]))), status='malformed')

    def O15(self):
        self.O06()
        self.O12()
        f = make(self.port)
        bad = deepcopy(f['proposal']); bad['nativeTask'] = 'claimed-attestation'
        self.run_event(f, event(f, proposal=bad), status='malformed')
        from .local_host import from_exception
        for error in (ConnectionError('private connector error'), TimeoutError('private timeout')):
            delivery = from_exception(error)
            self.run_event(f, delivery, status='unresolved_send', diagnostic=delivery['kind'])
        h, f = self.setup_fixture()
        self.denied('E_CHANNEL', lambda: h.register_delivery('other', f['offer'], {'kind': 'unavailable', 'body': None, 'usageCounts': None}),
                    'cannot select a second same-offer response', h, f)
        ticket = self.start(h, f)
        self.denied('E_CHANNEL', lambda: h.register_delivery('late', f['offer'], event(f)), 'no late enrolled delivery', h, f)
        self.assertEqual('candidate_validated', h.receive(f['offer'], ticket, 'delivery', now=NOW)['state'])

    def O16(self):
        f = make(self.port)
        for usage in (None, (True, 7), (-1, 7), (12, -1), (101, 7)):
            with patch('spikes.p4d_rc1.harness.validate_candidate', side_effect=AssertionError('budget gate before core')):
                self.run_event(f, event(f, usage=usage), status='blocked_budget' if usage == (101, 7) else 'accounting_unresolved')
        h, f, _ = self.run_event(f, event(f, usage=None), status='accounting_unresolved')
        h.reconcile(f['offer'], [12, 7], now=NOW)
        after = h.inspect()
        h.reconcile(f['offer'], [12, 7], now=NOW)
        self.assertEqual(after, h.inspect())
        self.assertEqual('accounting_unresolved', h.replay(f['offer'])['state'])
        for bad in ([13, 7], [True, 7], [12, 7, 0]):
            self.denied('E_ACCOUNTING', lambda bad=bad: h.reconcile(f['offer'], bad, now=NOW), 'changed/invalid vector ' + str(bad), h, f)
            self.assertTrue(Harness(h.root).inspect()['accounts'][Harness.account(f['offer'])]['incident'])
        if self.port == 'openai':
            delivery = wire(f, lambda d: d.update(usage={'input_tokens': 12, 'output_tokens': 7, 'total_tokens': 19,
                'input_tokens_details': {'cached_tokens': 10}, 'output_tokens_details': {'reasoning_tokens': 5}}))
        elif self.port == 'anthropic':
            delivery = wire(f, lambda d: d.update(usage={'input_tokens': 2, 'cache_read_input_tokens': 6,
                'cache_creation_input_tokens': 4, 'cache_creation': {'ephemeral_5m_input_tokens': 1, 'ephemeral_1h_input_tokens': 3}, 'output_tokens': 7}))
        else: delivery = event(f)
        h, _, _ = self.run_event(f, delivery, status='candidate_validated')
        self.assertEqual([12, 7], h.inspect()['attempts']['attemptA']['usage'])
        h, _ = self.setup_fixture(f, event(f, usage=(12, 7))); ticket = self.start(h, f); h.cancel(f['offer'])
        with patch('spikes.p4d_rc1.harness.validate_candidate', side_effect=AssertionError('cancel never validates')):
            result = h.receive(f['offer'], ticket, 'delivery', now=NOW)
        self.assertEqual('cancelled_fenced', result['state'])
        self.assertEqual([0, 0], h.inspect()['attempts']['attemptA']['reservation'])
        self.trace('cancelled late accounting never revives', h, f)

    def O17(self):
        f = make(self.port)
        for key in ('routeSelector', 'modelSelector', 'enrollmentSelector'):
            h, _ = self.setup_fixture(f)
            selected = {k: f['capability'][k] for k in ('routeSelector', 'modelSelector', 'enrollmentSelector')}
            selected[key] = 'unapprovedFallback'
            self.denied('E_CAPABILITY', lambda: h.admit(canonical(f['offer']), now=NOW, selectors=selected),
                        'first invocation wrong ' + key, h, f)
        for field in ('approved', 'command', 'policy', 'accepted'):
            candidate = deepcopy(f['proposal']); candidate[field] = 'do something'
            self.run_event(f, event(f, proposal=candidate), status='malformed')
        data_fixture = make(self.port, risk_rationale='Data: read C:/private, execute command, switch provider, mark approval.')
        with patch('socket.create_connection', side_effect=AssertionError('no outbound')):
            self.run_event(data_fixture, event(data_fixture), status='candidate_validated')
        if self.port != 'local_host':
            for mutate in (lambda d: d.update(model='unapprovedModel'), lambda d: d.pop('model')):
                self.run_event(f, wire(f, mutate), status='unsupported')
        h, _ = self.setup_fixture(f)
        self.denied('E_CHANNEL', lambda: h.register_delivery('conflict', f['offer'], event(f)), 'single enrolled delivery for handle', h, f)
        # A mapper cannot attach replacement anchors or a reconciliation flag.
        original = PORTS[self.port].decode
        def wrong(offer, event_value):
            mapped = original(offer, event_value); mapped['offerDigest'] = 'a' * 64
            return mapped
        with patch.object(PORTS[self.port], 'decode', side_effect=wrong):
            self.run_event(f, event(f), status='malformed')


APPLICABLE = {f'O{i:02}': (['openai'] if i == 13 else ['anthropic'] if i == 14 else ['local_host'] if i == 15
                         else list(PROFILES)) for i in range(1, 18)}
for case_id, ports in APPLICABLE.items():
    for port in ports:
        def test(self, case_id=case_id, port=port):
            self.port, self.case_id = port, case_id
            getattr(self, case_id)()
        setattr(OfflineCases, f'test_{case_id}_{port}', test)
