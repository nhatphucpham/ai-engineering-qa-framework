"""Strict JSON file intake shared by assessment and reference-report CLIs."""

import json


def load_json(path):
    def reject_constant(_value):
        raise ValueError('Non-finite JSON')

    def unique_members(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON member')
            value[key] = item
        return value

    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant,
                      object_pairs_hook=unique_members)
