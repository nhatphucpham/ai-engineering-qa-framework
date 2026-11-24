"""Finite canonical JSON and safe candidate application diagnostics."""
import hashlib
import json
import re

VERSION = 'm50-application-1.1.0'
MAX_BYTES = 1024 * 1024
OPERATIONS = frozenset(('session_login', 'session_refresh', 'session_logout', 'session_change_password',
    'account_create', 'account_set_enabled', 'account_set_role', 'account_reset_password',
    'project_create', 'project_configure', 'grant_issue', 'grant_revoke', 'service_enroll', 'service_revoke',
    'intake_snapshot', 'run_start', 'run_cancel', 'run_read', 'report_read', 'source_read', 'report_export',
    'events', 'assessment_accept', 'worker_claim', 'worker_renew', 'worker_admit', 'worker_observe_cleanup', 'worker_submit', 'worker_fail'))
OPERATIONS = OPERATIONS | frozenset(('session_read', 'project_list', 'project_read', 'run_list', 'collector_record', 'worker_recover_claim'))
PUBLIC_OPERATIONS = frozenset(('session_login', 'session_refresh'))


class Error(ValueError):
    def __init__(self, code='E_INPUT'):
        self.code = code
        super().__init__(code)


def require(condition, code='E_INPUT'):
    if not condition:
        raise Error(code)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise Error('E_INPUT') from exc


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def strict_json(raw, limit=MAX_BYTES):
    require(isinstance(raw, bytes) and len(raw) <= limit)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    def invalid(_):
        raise Error('E_INPUT')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
        canonical(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Error('E_INPUT') from exc


def identifier(value):
    require(isinstance(value, str) and re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}', value))
    return value


def exact(body, fields):
    require(isinstance(body, dict) and set(body) == set(fields.split()))
    canonical(body)
    return body
