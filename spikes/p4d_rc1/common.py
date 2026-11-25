"""Bounded, safe adapter diagnostics; reuse candidate canonical JSON."""
from runtime_candidate.common import canonical, digest, sha, strict_json

VERSION = 'p4d-rc1-1.0.0'
LIMIT = 65536
PROFILES = {'local_host': 'local-completion-1', 'openai': 'openai-responses-1',
            'anthropic': 'anthropic-messages-1'}
PAIRS = {('candidate_received', 'none'), ('refused', 'refusal'),
         ('incomplete', 'output_limit'), ('incomplete', 'context_limit'), ('incomplete', 'terminal_incomplete'),
         ('malformed', 'parse'), ('malformed', 'shape'), ('unsupported', 'output_kind'), ('unsupported', 'stop_reason'),
         *(('provider_error', code) for code in ('auth', 'permission', 'rate_limit', 'overload', 'service', 'unavailable')),
         ('unresolved_send', 'timeout'), ('unresolved_send', 'transport_loss')}


class Rejected(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code='E_INPUT'):
    if not condition:
        raise Rejected(code)


def exact(value, fields):
    need(isinstance(value, dict) and set(value) == set(fields.split()))


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def parse(raw):
    try:
        return strict_json(raw, LIMIT)
    except ValueError as exc:
        raise Rejected('E_INPUT') from exc


def counts(input_tokens=None, output_tokens=None):
    if not integer(input_tokens) or not integer(output_tokens):
        input_tokens = output_tokens = None
    return {'mode': 'authored_fixture', 'inputTokens': input_tokens, 'outputTokens': output_tokens}


def result(offer, raw, outcome, diagnostic, *, proposal=None, usage=None, model=None, request_id=None):
    model = model if isinstance(model, str) and len(model) <= 256 else None
    request_id = request_id if isinstance(request_id, str) and len(request_id) <= 256 else None
    value = {'version': VERSION, 'attemptId': offer['attemptId'], 'offerDigest': digest(offer),
             'port': offer['port'], 'profile': offer['profile'], 'outcome': outcome, 'diagnostic': diagnostic,
             'responseSha256': sha(raw) if raw is not None else None, 'proposal': proposal,
             'usage': usage or counts(), 'provenance': {'origin': 'authored_fixture',
                                                      'model': model, 'requestId': request_id}}
    need(len(canonical(value)) <= LIMIT, 'E_RESPONSE_SIZE')
    return value


def validate_result(value, offer, raw):
    exact(value, 'version attemptId offerDigest port profile outcome diagnostic responseSha256 proposal usage provenance')
    need(value['version'] == VERSION and value['attemptId'] == offer['attemptId'] and
         value['offerDigest'] == digest(offer) and value['port'] == offer['port'] and
         value['profile'] == offer['profile'] and value['responseSha256'] == (sha(raw) if raw is not None else None), 'E_INTEGRITY')
    need((value['outcome'], value['diagnostic']) in PAIRS, 'E_INTEGRITY')
    need((isinstance(value['proposal'], dict) if value['outcome'] == 'candidate_received' else value['proposal'] is None), 'E_INTEGRITY')
    exact(value['usage'], 'mode inputTokens outputTokens')
    need(value['usage']['mode'] == 'authored_fixture' and
         all(v is None or integer(v) for k, v in value['usage'].items() if k != 'mode'), 'E_INTEGRITY')
    exact(value['provenance'], 'origin model requestId')
    need(value['provenance']['origin'] == 'authored_fixture' and all(
         v is None or isinstance(v, str) and len(v) <= 256 for k, v in value['provenance'].items() if k != 'origin'), 'E_INTEGRITY')
    need(len(canonical(value)) <= LIMIT, 'E_RESPONSE_SIZE')


def proposal(raw):
    try:
        value = parse(raw)
    except Rejected:
        return None, 'parse'
    if not isinstance(value, dict):
        return None, 'shape'
    return value, None


def http_failure(status, port):
    if type(status) is not int or not 100 <= status <= 599:
        return 'malformed', 'shape'
    if not 200 <= status < 300:
        code = {401: 'auth', 403: 'permission', 429: 'rate_limit'}.get(status, 'service')
        if port == 'anthropic' and status == 529:
            code = 'overload'
        return 'provider_error', code
    return None


def transport_failure(kind):
    return {'timeout': ('unresolved_send', 'timeout'),
            'transport_loss': ('unresolved_send', 'transport_loss')}.get(kind)
