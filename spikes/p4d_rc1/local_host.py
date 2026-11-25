"""Local fixture completion events, independent of HTTP provider dialects."""
from .common import canonical, counts, exact, need, proposal, result


def encode(offer, selectors):
    return canonical({'kind': 'local_completion', 'context': {'job': offer['job'],
                                                           'responseContract': offer['responseContract']}})


def from_exception(error):
    """Map a trusted authored connector observation, never its private exception text."""
    need(isinstance(error, OSError))
    return {'kind': 'timeout' if isinstance(error, TimeoutError) else 'transport_loss',
            'body': None, 'usageCounts': None}


def decode(offer, event):
    exact(event, 'kind body usageCounts')
    kind, raw, usage_raw = event['kind'], event['body'], event['usageCounts']
    need(raw is None or isinstance(raw, bytes))
    usage = counts()
    if isinstance(usage_raw, dict) and set(usage_raw) == {'inputTokens', 'outputTokens'}:
        usage = counts(usage_raw['inputTokens'], usage_raw['outputTokens'])
    mapped = {'refusal': ('refused', 'refusal'), 'output_limit': ('incomplete', 'output_limit'),
              'unavailable': ('provider_error', 'unavailable'), 'auth_error': ('provider_error', 'auth'),
              'permission_error': ('provider_error', 'permission'), 'rate_limit': ('provider_error', 'rate_limit'),
              'service_error': ('provider_error', 'service'), 'timeout': ('unresolved_send', 'timeout'),
              'transport_loss': ('unresolved_send', 'transport_loss')}
    if kind in mapped:
        need((kind in ('refusal', 'output_limit') or raw is None) and (kind != 'refusal' or raw is not None))
        return result(offer, raw, *mapped[kind], usage=usage)
    need(kind == 'completion' and isinstance(raw, bytes))
    candidate, error = proposal(raw)
    return result(offer, raw, 'malformed' if error else 'candidate_received', error or 'none',
                  proposal=candidate, usage=usage)
