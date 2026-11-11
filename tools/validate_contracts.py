"""Compatibility CLI and imports backed by the shared qa_core module."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_core.contracts import *  # Preserve existing tooling imports.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.bundle.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        print(json.dumps({'valid': False, 'errors': [{'code': 'E_INPUT', 'message': 'Cannot read UTF-8 JSON input'}]}))
        return 2
    print(json.dumps({'valid': not errors, 'errors': errors}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
