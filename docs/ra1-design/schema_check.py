"""RA1 request shape/strict wire checks only, never authentication or DB state."""
from pathlib import Path
from jsonschema import Draft202012Validator
from runtime_candidate.common import canonical, strict_json

ROOT = Path(__file__).resolve().parents[2]
INTEGER_KEYS = {'expected_epoch', 'expected_config', 'expected_ra_policy', 'expected_attempt_version',
                'base_policy_version', 'input_bound', 'output_bound', 'attempt_seconds',
                'max_invocations', 'max_submissions', 'max_response_bytes'}


def strict_numbers(value):
    if isinstance(value, dict):
        return all((key not in INTEGER_KEYS or type(child) is int) and strict_numbers(child) for key, child in value.items())
    if isinstance(value, list):
        return all(strict_numbers(child) for child in value)
    return True


def unique_policy_ports(request):
    ports = request.get('params', {}).get('policy', {}).get('ports', [])
    return len({p['port'] for p in ports}) == len(ports)


def suite(schema_path, specimens_path):
    schema = strict_json((ROOT / schema_path).read_bytes())
    def local_refs(value):
        if isinstance(value, dict):
            assert '$ref' not in value or value['$ref'].startswith('#/'), 'external ref unsupported'
            for child in value.values(): local_refs(child)
        elif isinstance(value, list):
            for child in value: local_refs(child)
    local_refs(schema)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    fixtures = strict_json((ROOT / specimens_path).read_bytes())
    rows = []
    for case in fixtures['cases']:
        raw = bytes.fromhex(case['rawHex']) if 'rawHex' in case else case['raw'].encode('utf-8') if 'raw' in case else canonical(case['request'])
        if 'padTo' in case:
            raw += b' ' * (case['padTo'] - len(raw))
        try:
            request = strict_json(raw, 65536)
        except ValueError:
            accepted, stage = False, 'json'
        else:
            if not validator.is_valid(request): accepted, stage = False, 'shape'
            elif not strict_numbers(request) or not unique_policy_ports(request): accepted, stage = False, 'wire'
            else: accepted, stage = True, 'shape_and_wire'
        assert accepted == case['expectedAccepted'] and stage == case['expectedStage'], case['id']
        rows.append({'id': case['id'], 'accepted': accepted, 'stage': stage, 'status': 'PASS'})
    positives = {case['request']['operation'] for case in fixtures['cases'] if case['expectedAccepted']}
    assert positives == set(schema['properties']['operation']['enum'])
    return {'scope': 'request JSON/shape/strict-integer specimens only; no authority or transaction proof',
            'status': 'PASS', 'operations': len(positives), 'cases': rows}


def run():
    return {'status': 'PASS', 'authority': suite('schemas/ra1-authority-request-v1.schema.json', 'docs/ra1-design/request-specimens.json'),
            'optInRead': suite('schemas/ra1-read-request-v1.schema.json', 'docs/ra1-design/read-specimens.json')}
