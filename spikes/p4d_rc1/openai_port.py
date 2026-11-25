"""Responses-shaped offline fixtures. Never imports an OpenAI SDK/client."""
from .common import (canonical, counts, exact, http_failure, integer, need, parse,
                     proposal, Rejected, result, transport_failure)


def encode(offer, selectors):
    text = canonical({'job': offer['job'], 'responseContract': offer['responseContract']}).decode('utf-8')
    return canonical({'model': selectors['modelSelector'], 'stream': False, 'store': False,
                      'max_output_tokens': offer['budget']['maxOutputTokens'], 'tools': [],
                      'truncation': 'disabled', 'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}]})


def usage_counts(value):
    if not isinstance(value, dict):
        return counts()
    inp, out = value.get('input_tokens'), value.get('output_tokens')
    for key, total, child in [('input_tokens_details', inp, 'cached_tokens'),
                              ('output_tokens_details', out, 'reasoning_tokens')]:
        detail = value.get(key)
        if detail is not None and (not isinstance(detail, dict) or
                any(not integer(v) for v in detail.values()) or not integer(total) or
                (child in detail and detail[child] > total)):
            return counts()
    if 'total_tokens' in value and (not integer(inp) or not integer(out) or
                                   not integer(value['total_tokens']) or value['total_tokens'] != inp + out):
        return counts()
    return counts(inp, out)


def decode(offer, event):
    exact(event, 'kind status body requestId')
    raw = event['body']
    need(raw is None or isinstance(raw, bytes))
    failed = transport_failure(event['kind'])
    if failed:
        need(raw is None)
        return result(offer, raw, *failed)
    need(event['kind'] == 'http')
    failed = http_failure(event['status'], 'openai')
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
    if data.get('object') != 'response':
        return finish('malformed', 'shape')
    if 'status' not in data or data['status'] is None:
        return finish('malformed', 'shape')
    faulted = data.get('error') is not None or data.get('status') == 'failed'
    items = data.get('output', [] if data['status'] == 'incomplete' or faulted else None)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        return finish('malformed', 'shape')
    messages = [item for item in items if item.get('type') == 'message']
    blocks = []
    for message in messages:
        content = message.get('content')
        if not isinstance(content, list) or any(not isinstance(b, dict) for b in content):
            return finish('malformed', 'shape')
        blocks.extend(content)
    if any(b.get('type') == 'refusal' for b in blocks):
        return finish('refused', 'refusal')
    if faulted:
        return finish('provider_error', 'service')
    if data.get('status') == 'incomplete' or data.get('incomplete_details') is not None:
        details = data.get('incomplete_details')
        reason = details.get('reason') if isinstance(details, dict) else None
        return finish('incomplete', 'output_limit' if reason == 'max_output_tokens' else 'terminal_incomplete')
    if data.get('status') != 'completed':
        return finish('unsupported', 'stop_reason')
    if len(items) == 1 and items[0].get('type') != 'message' and all(k in items[0] for k in ('role', 'status', 'content')):
        return finish('malformed', 'shape')
    if any(item.get('type') not in ('message', 'reasoning') for item in items):
        return finish('unsupported', 'output_kind')
    if len(messages) != 1 or messages[0].get('role') != 'assistant':
        return finish('malformed', 'shape')
    if messages[0].get('status') == 'incomplete':
        return finish('incomplete', 'terminal_incomplete')
    if messages[0].get('status') != 'completed':
        return finish('malformed', 'shape')
    if any(b.get('type') != 'output_text' for b in blocks):
        return finish('unsupported', 'output_kind')
    if len(blocks) != 1 or not isinstance(blocks[0].get('text'), str):
        return finish('malformed', 'shape')
    candidate, error = proposal(blocks[0]['text'].encode('utf-8'))
    return finish('malformed' if error else 'candidate_received', error or 'none', candidate)
