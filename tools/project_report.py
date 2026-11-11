"""Compatibility CLI and imports backed by the shared qa_core module."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_core.reports import *  # Preserve existing tooling imports.
from json_input import load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('assessment', type=Path)
    parser.add_argument('--check', type=Path, help='Validate a report against both input files')
    args = parser.parse_args()
    try:
        bundle, assessment = load_json(args.bundle), load_json(args.assessment)
        if args.check:
            errors = validate_report(load_json(args.check), bundle, assessment)
            print(json.dumps({'processingStatus': 'report_validated' if not errors else 'input_error',
                              'valid': not errors, 'errors': errors}, indent=2))
            return 2 if errors else 0
        report = create_report(bundle, assessment)
    except (OSError, ValueError, UnicodeError, RecursionError):
        # Do not echo paths, raw input, schema paths or exception strings.
        print(json.dumps({'processingStatus': 'input_error',
                          'errors': [{'code': 'E_INPUT', 'message': 'Cannot derive a report from supplied JSON'}]}, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    return 0 if report['assessment']['verification'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
