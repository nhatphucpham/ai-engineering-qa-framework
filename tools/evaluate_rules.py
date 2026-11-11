"""Compatibility CLI and imports backed by the shared qa_core module."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_core.rules import *  # Preserve existing tooling imports.
from json_input import load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('assessment', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_json(args.bundle), load_json(args.assessment))
    except (OSError, ValueError, RecursionError) as error:
        details = error.errors if isinstance(error, AssessmentError) else [{'code': 'E_INPUT', 'message': 'Cannot read input JSON'}]
        print(json.dumps({'processingStatus': 'input_error', 'errors': details}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['verification'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
