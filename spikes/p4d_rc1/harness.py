"""Disposable trusted-filesystem ledger. Emits authored fixture bytes, never calls a model."""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import threading
import uuid

from . import anthropic_port, local_host, openai_port
from .common import (VERSION, LIMIT, Rejected, canonical, digest, integer, need, parse,
                     result, sha, validate_result)
from .contracts import check_scope, timestamp, validate_candidate, validate_offer

PORTS = {'local_host': local_host, 'openai': openai_port, 'anthropic': anthropic_port}
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def serial_event(event):
    event = deepcopy(event)
    if isinstance(event.get('body'), bytes):
        event['body'] = {'hex': event['body'].hex()}
    return event


def materialize(event):
    event = deepcopy(event)
    if isinstance(event.get('body'), dict):
        need(set(event['body']) == {'hex'}, 'E_UNRESOLVED')
        event['body'] = bytes.fromhex(event['body']['hex'])
    return event


class Harness:
    """All setup methods are operator-only fixture facilities, not service operations."""
    def __init__(self, root, *, create=False):
        self.root = Path(root).resolve()
        self.session = uuid.uuid4().hex
        with _LOCKS_GUARD:
            self.lock = _LOCKS.setdefault(str(self.root), threading.RLock())
        if create:
            self.root.mkdir(exist_ok=False)
            self._write('marker.json', {'version': VERSION, 'kind': 'offline-authored-fixture'})
            self._write('state.json', {'registrations': {}, 'deliveries': {}, 'accounts': {}, 'attempts': {},
                                       'authority': {}, 'applicationEffects': 0})
        need(self._read('marker.json') == {'version': VERSION, 'kind': 'offline-authored-fixture'}, 'E_UNRESOLVED')
        self._read('state.json')

    def _read(self, name):
        try:
            from runtime_candidate.common import strict_json
            raw = (self.root / name).read_bytes()
            envelope = strict_json(raw, 4 * 1024 * 1024)
            need(set(envelope) == {'state', 'sha256'} and digest(envelope['state']) == envelope['sha256'], 'E_UNRESOLVED')
            return envelope['state']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise Rejected('E_UNRESOLVED') from exc

    def _write(self, name, state):
        raw = canonical({'state': state, 'sha256': digest(state)})
        need(len(raw) <= 4 * 1024 * 1024, 'E_BUDGET')
        temp = self.root / (uuid.uuid4().hex + '.tmp')
        with temp.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, self.root / name)

    @contextmanager
    def unit(self, *, write=False):
        with self.lock:
            path = self.root / '.mutation-lock'
            try:
                path.mkdir()
            except FileExistsError as exc:
                raise Rejected('E_UNRESOLVED') from exc
            try:
                state = self._read('state.json')
                before = digest(state)
                yield state
                if write and digest(state) != before:
                    self._write('state.json', state)
            finally:
                path.rmdir()

    @staticmethod
    def account(offer):
        target = offer['target']
        return digest([target['projectId'], target['runId'], target['dataPolicyVersion']])

    def register(self, offer, sources, capability, *, expected_bundle_digest, omitted_check_ids,
                 capacity=(400, 400), scope=None):
        """Trusted setup can register negative/malformed offers; admission still validates."""
        with self.unit(write=True) as state:
            aid = offer['attemptId']
            need(aid not in state['registrations'], 'E_CONFLICT')
            scope = scope or {'projectId': offer['target']['projectId'], 'port': offer['port'],
                              'sourceManifest': deepcopy(offer['sourceManifest']),
                              'expectedBundleDigest': expected_bundle_digest,
                              'omittedCheckIds': list(omitted_check_ids)}
            row = {'offer': deepcopy(offer), 'offerDigest': digest(offer), 'sources': deepcopy(sources),
                   'scope': deepcopy(scope), 'capability': deepcopy(capability)}
            state['registrations'][aid] = row
            account = self.account(offer)
            if account not in state['accounts']:
                need(len(capacity) == 2 and all(integer(n) for n in capacity))
                state['accounts'][account] = {'capacity': list(capacity), 'consumed': [0, 0], 'incident': False}
                state['authority'][account] = {'enabled': True, 'enrolled': True,
                    'ports': list(PORTS), 'sourceIds': sorted(sources),
                    'configVersion': offer['target']['projectConfigVersion'],
                    'policyVersion': offer['target']['dataPolicyVersion']}
            state['attempts'][aid] = {'offerDigest': digest(offer), 'account': account,
                'state': 'offered', 'history': ['offered'], 'reservation': [0, 0], 'reconciled': False,
                'calls': 0, 'releasedBytes': 0, 'handle': None, 'receipt': None, 'intentOpen': False}

    def register_delivery(self, delivery_id, offer, event):
        from runtime_candidate.common import identifier
        identifier(delivery_id)
        with self.unit(write=True) as state:
            need(delivery_id not in state['deliveries'], 'E_CONFLICT')
            row, attempt = self._bound(state, offer)
            need(attempt['state'] == 'offered' and not any(
                 d['offerDigest'] == digest(offer) for d in state['deliveries'].values()), 'E_CHANNEL')
            state['deliveries'][delivery_id] = {'offerDigest': digest(offer), 'port': offer['port'],
                'profile': offer['profile'], 'event': serial_event(event), 'eventDigest': digest(serial_event(event))}

    def authority(self, offer, **changes):
        """Trusted fault injector; no real user/project policy is modified."""
        with self.unit(write=True) as state:
            current = state['authority'][self.account(offer)]
            need(set(changes) <= set(current))
            current.update(deepcopy(changes))

    @staticmethod
    def transition(attempt, status):
        attempt['state'] = status
        attempt['history'].append(status)

    def _bound(self, state, offer):
        aid = offer['attemptId']
        need(aid in state['registrations'], 'E_INTEGRITY')
        row, attempt = state['registrations'][aid], state['attempts'][aid]
        need(row['offerDigest'] == digest(row['offer']) == attempt['offerDigest'] == digest(offer), 'E_CONFLICT')
        return row, attempt

    @staticmethod
    def _policy(state, offer, row, attempt):
        try:
            check_scope(offer, row, state['authority'][attempt['account']])
        except (ValueError, KeyError, TypeError, RecursionError) as exc:
            raise Rejected(getattr(exc, 'code', 'E_INTEGRITY')) from exc

    def admit(self, raw_offer, *, now, selectors=None, fault=None):
        try:
            offer = parse(raw_offer)
            validate_offer(offer)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            raise Rejected(getattr(exc, 'code', 'E_INPUT')) from exc
        with self.unit(write=True) as state:
            row, attempt = self._bound(state, offer)
            self._policy(state, offer, row, attempt)
            if attempt['state'] != 'offered':
                return self._receipt(state, offer, row, attempt)
            if now >= timestamp(offer['deadlineUtc']):
                self.transition(attempt, 'expired_fenced')
                return {'state': attempt['state']}
            configured = {key: row['capability'][key] for key in
                          ('routeSelector', 'modelSelector', 'enrollmentSelector')}
            need(selectors is None or selectors == configured, 'E_CAPABILITY')
            deliveries = [key for key, d in state['deliveries'].items() if
                          (d['offerDigest'], d['port'], d['profile']) ==
                          (digest(offer), offer['port'], offer['profile'])]
            need(len(deliveries) == 1, 'E_CAPABILITY')
            account = state['accounts'][attempt['account']]
            required = [offer['budget']['inputTokenBound'], offer['budget']['maxOutputTokens']]
            reserved = [sum(a['reservation'][i] for a in state['attempts'].values()
                            if a['account'] == attempt['account']) for i in (0, 1)]
            need(all(required[i] + reserved[i] + account['consumed'][i] <= account['capacity'][i]
                     for i in (0, 1)), 'E_BUDGET')
            # Capacity denial stays distinct; a funded but uncertain account is still fenced.
            need(not account['incident'] and not any(a['account'] == attempt['account'] and a['intentOpen']
                 for a in state['attempts'].values()), 'E_UNRESOLVED')
            if fault == 'before_intent':
                raise Rejected('E_INJECTED_BEFORE_INTENT')
            attempt['reservation'] = required
            attempt['intentOpen'] = True
            attempt['handle'] = uuid.uuid4().hex
            attempt['issuerSession'] = self.session
            attempt['expectedDeliveryId'] = deliveries[0]
            self.transition(attempt, 'send_intent')
            handle = attempt['handle']
        if fault == 'after_intent':
            raise Rejected('E_INJECTED_AFTER_INTENT')
        return {'state': 'send_intent', 'handle': handle}

    def emit(self, offer, handle, *, now, selectors=None):
        with self.unit(write=True) as state:
            row, attempt = self._bound(state, offer)
            self._policy(state, offer, row, attempt)
            need(attempt['handle'] == handle and attempt['state'] == 'send_intent' and attempt['calls'] == 0, 'E_CONFLICT')
            need(attempt.get('issuerSession') == self.session, 'E_UNRESOLVED')
            if now >= timestamp(offer['deadlineUtc']):
                self.transition(attempt, 'expired_fenced')
                return {'state': 'expired_fenced'}
            configured = {key: row['capability'][key] for key in
                          ('routeSelector', 'modelSelector', 'enrollmentSelector')}
            need(selectors is None or selectors == configured, 'E_CAPABILITY')
            raw = PORTS[offer['port']].encode(offer, configured)
            need(len(raw) <= LIMIT, 'E_BUDGET')
            attempt['requestHex'] = raw.hex()
            attempt['requestDigest'] = sha(raw)
            attempt['calls'] = 1
            attempt['releasedBytes'] = len(raw)
            return {'state': 'send_intent', 'request': raw}

    def receive(self, offer, handle, delivery_id, *, now, validation_now=None):
        with self.unit(write=True) as state:
            row, attempt = self._bound(state, offer)
            self._policy(state, offer, row, attempt)
            need(attempt['handle'] == handle, 'E_CHANNEL')
            need(attempt.get('expectedDeliveryId') == delivery_id, 'E_CHANNEL')
            need(delivery_id in state['deliveries'], 'E_CHANNEL')
            delivery = state['deliveries'][delivery_id]
            need(digest(delivery['event']) == delivery['eventDigest'], 'E_UNRESOLVED')
            need((delivery['offerDigest'], delivery['port'], delivery['profile']) ==
                 (digest(offer), offer['port'], offer['profile']), 'E_CHANNEL')
            if attempt['receipt'] is not None:
                need(attempt['deliveryId'] == delivery_id, 'E_CONFLICT')
                return self._receipt(state, offer, row, attempt)
            need(attempt['calls'] == 1 and attempt['state'] in
                 ('send_intent', 'cancelled_fenced', 'expired_fenced'), 'E_CONFLICT')
            fenced = attempt['state'] if attempt['state'] in ('cancelled_fenced', 'expired_fenced') else None
            if attempt.get('issuerSession') != self.session:
                fenced = fenced or 'unresolved_send'
            if max(now, validation_now if validation_now is not None else now) >= timestamp(offer['deadlineUtc']):
                fenced = fenced or 'expired_fenced'
            event = materialize(delivery['event'])
            raw = event.get('body')
            if raw is not None and len(raw) > offer['budget']['maxResponseBytes']:
                mapped = result(offer, raw, 'malformed', 'shape')
            else:
                try:
                    mapped = PORTS[offer['port']].decode(offer, event)
                    validate_result(mapped, offer, raw)
                except (ValueError, TypeError, KeyError, UnicodeError):
                    mapped = result(offer, raw, 'malformed', 'shape')
            validation = None
            usage = [mapped['usage']['inputTokens'], mapped['usage']['outputTokens']]
            known_usage = all(integer(n) for n in usage)
            over_bound = known_usage and any(usage[i] > attempt['reservation'][i] for i in (0, 1))
            if mapped['outcome'] == 'candidate_received' and not fenced:
                capability = row['capability']
                if capability['requireModelEcho'] and mapped['provenance']['model'] not in capability['responseModelMap']:
                    mapped['outcome'], mapped['diagnostic'], mapped['proposal'] = 'unsupported', 'output_kind', None
                elif known_usage and not over_bound:
                    try:
                        validation = validate_candidate(offer, mapped['proposal'], row['scope']['expectedBundleDigest'])
                    except (ValueError, KeyError, TypeError):
                        mapped['outcome'], mapped['diagnostic'], mapped['proposal'] = 'malformed', 'shape', None
            status = mapped['outcome']
            if known_usage:
                if over_bound:
                    self._accounting_incident(state, attempt)
                    if status == 'candidate_received':
                        status = 'blocked_budget'
                else:
                    self._reconcile(state, attempt, usage)
            elif status == 'candidate_received':
                status = 'accounting_unresolved'
            if status == 'candidate_received':
                status = 'candidate_validated'
            # Local cancellation/deadline always dominates result/accounting for acceptance.
            status = fenced or status
            self.transition(attempt, status)
            receipt = {'version': VERSION, 'offerDigest': digest(offer), 'state': status,
                       'result': mapped, 'validation': validation if status == 'candidate_validated' else None,
                       'remoteTermination': 'unknown', 'applicationEffects': 0}
            if len(canonical(receipt)) > LIMIT:
                mapped = result(offer, raw, 'malformed', 'shape')
                status = fenced or 'malformed'
                receipt.update(state=status, result=mapped, validation=None)
                # Any observed counts were already reconciled. Receipt size cannot undo accounting.
                attempt['state'] = status
                attempt['history'][-1] = status
            attempt['receipt'] = receipt
            attempt['receiptDigest'] = digest(receipt)
            attempt['deliveryId'] = delivery_id
            return deepcopy(receipt)

    @staticmethod
    def _accounting_incident(state, attempt):
        attempt['accountingIncident'] = True
        state['accounts'][attempt['account']]['incident'] = True

    @staticmethod
    def _reconcile(state, attempt, usage):
        if not isinstance(usage, list) or len(usage) != 2 or not all(integer(n) for n in usage):
            Harness._accounting_incident(state, attempt)
            return False
        if attempt['reconciled']:
            if attempt['usage'] != usage:
                Harness._accounting_incident(state, attempt)
                return False
            return True
        if not all(usage[i] <= attempt['reservation'][i] for i in (0, 1)):
            Harness._accounting_incident(state, attempt)
            return False
        account = state['accounts'][attempt['account']]
        account['consumed'] = [account['consumed'][i] + usage[i] for i in (0, 1)]
        attempt['reservation'] = [0, 0]
        attempt['reconciled'] = True
        attempt['usage'] = list(usage)
        attempt['intentOpen'] = False
        return True

    def reconcile(self, offer, usage, *, now):
        """Operator-observed late fixture counts only; never a second model submission."""
        with self.unit(write=True) as state:
            row, attempt = self._bound(state, offer)
            self._policy(state, offer, row, attempt)
            need(attempt['receipt'] is not None, 'E_UNRESOLVED')
            self._receipt(state, offer, row, attempt)
            ok = self._reconcile(state, attempt, usage)
            # Accounting can release balance but this bounded harness never promotes a late
            # candidate or edits the immutable original receipt. Explicit future policy needed.
            status = attempt['state']
        need(ok, 'E_ACCOUNTING')
        return {'reconciled': True, 'state': status}

    def _receipt(self, state, offer, row, attempt):
        self._policy(state, offer, row, attempt)
        receipt = attempt['receipt']
        if receipt is not None:
            try:
                need(digest(receipt) == attempt.get('receiptDigest') and receipt['offerDigest'] == digest(offer)
                     and receipt['state'] == attempt['state'], 'E_UNRESOLVED')
                delivery_id = attempt['deliveryId']
                need(delivery_id == attempt['expectedDeliveryId'] and delivery_id in state['deliveries'], 'E_UNRESOLVED')
                delivery = state['deliveries'][delivery_id]
                need(delivery['offerDigest'] == digest(offer) and delivery['port'] == offer['port'] and
                     delivery['profile'] == offer['profile'] and digest(delivery['event']) == delivery['eventDigest'], 'E_UNRESOLVED')
                raw = materialize(delivery['event'])['body']
                validate_result(receipt['result'], offer, raw)
                need(attempt['calls'] == 1 and sha(bytes.fromhex(attempt['requestHex'])) == attempt['requestDigest'], 'E_UNRESOLVED')
            except (ValueError, KeyError, TypeError) as exc:
                raise Rejected('E_UNRESOLVED') from exc
            return deepcopy(receipt)
        if attempt['state'] == 'send_intent':
            return {'state': 'unresolved_send', 'remoteTermination': 'unknown'}
        need(attempt['state'] in ('offered', 'cancelled_fenced', 'expired_fenced'), 'E_UNRESOLVED')
        return {'state': attempt['state']}

    def replay(self, offer):
        with self.unit() as state:
            row, attempt = self._bound(state, offer)
            return self._receipt(state, offer, row, attempt)

    def cancel(self, offer):
        with self.unit(write=True) as state:
            row, attempt = self._bound(state, offer)
            self._policy(state, offer, row, attempt)
            need(attempt['receipt'] is None, 'E_CONFLICT')
            self.transition(attempt, 'cancelled_fenced')
            return {'state': 'cancelled_fenced', 'remoteTermination': 'unknown'}

    def inspect(self):
        with self.unit() as state:
            return deepcopy(state)
