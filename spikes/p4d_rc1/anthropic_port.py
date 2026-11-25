"""Messages-shaped offline fixtures. No Anthropic SDK/client or continuation."""
from .common import (canonical, counts, exact, http_failure, integer, need, parse,
                     proposal, Rejected, result, transport_failure)


def encode(offer, selectors):
    text = canonical({'job': offer['job'], 'responseContract': offer['responseContract']}).decode('utf-8')
    return canonical({'model': selectors['modelSelector'], 'stream': False,
                      'max_tokens': offer['budget']['maxOutputTokens'],
                      'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': text}]}]})


def usage_counts(value):
    if not isinstance(value, dict):
        return counts()
    fields = [value.get('input_tokens'), value.get('output_tokens'),
              value.get('cache_creation_input_tokens', 0), value.get('cache_read_input_tokens', 0)]
    if any(not integer(n) for n in fields):
        return counts()
    detail = value.get('cache_creation')
    if detail is not None and (not isinstance(detail, dict) or any(not integer(v) for v in detail.values())
                               or sum(detail.values()) != fields[2]):
        return counts()
    return counts(fields[0] + fields[2] + fields[3], fields[1])


def decode(offer, event):
    exact(event, 'kind status body requestId')
    raw = event['body']
    need(raw is None or isinstance(raw, bytes))
    failed = transport_failure(event['kind'])
    if failed:
        need(raw is None)
        return result(offer, raw, *failed)
    need(event['kind'] == 'http')
    failed = http_failure(event['status'], 'anthropic')
    if failed:
        return result(offer, raw, *failed, request_id=event['requestId'])
    try:
        data = parse(raw)
    except Rejected:
        return result(offer, raw, 'malformed', 'parse')
    if not isinstance(data, dict):
        return result(offer, raw, 'malformed', 'shape')
    usage = usage_counts(data.get('usage'))
    def finish(outcome, diagnostic, candidate=None):
        return result(offer, raw, outcome, diagnostic, proposal=candidate, usage=usage,
                      model=data.get('model'), request_id=event['requestId'])
    if data.get('type') != 'message' or data.get('role') != 'assistant':
        return finish('malformed', 'shape')
    stop = data.get('stop_reason')
    if stop is None:
        return finish('malformed', 'shape')
    if stop == 'refusal':
        return finish('refused', 'refusal')
    if stop in ('max_tokens', 'model_context_window_exceeded'):
        return finish('incomplete', 'output_limit' if stop == 'max_tokens' else 'context_limit')
    if stop != 'end_turn':
        return finish('unsupported', 'stop_reason')
    blocks = data.get('content')
    if not isinstance(blocks, list) or any(not isinstance(b, dict) for b in blocks):
        return finish('malformed', 'shape')
    if any(b.get('type') != 'text' for b in blocks):
        return finish('unsupported', 'output_kind')
    if len(blocks) != 1 or not isinstance(blocks[0].get('text'), str) or not blocks[0]['text']:
        return finish('malformed', 'shape')
    candidate, error = proposal(blocks[0]['text'].encode('utf-8'))
    return finish('malformed' if error else 'candidate_received', error or 'none', candidate)
