"""Synthetic internal report/completion harness; stdout only, no runtime side effects."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from json_input import load_json
from qa_core.application import prepare_report, check_prepared_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('assessment', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--report-id', required=True)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    try:
        bundle, assessment = load_json(args.bundle), load_json(args.assessment)
        context = {'run_id': args.run_id, 'report_id': args.report_id}
        if args.check:
            errors = check_prepared_report(load_json(args.check), bundle, assessment, **context)
            print(json.dumps({'processingStatus': 'input_error' if errors else 'proposal_validated',
                              'errors': errors}, indent=2))
            return 2 if errors else 0
        prepared = prepare_report(bundle, assessment, **context)
    except (OSError, ValueError, UnicodeError, RecursionError):
        print(json.dumps({'processingStatus': 'input_error', 'errors': [
            {'code': 'E_INPUT', 'message': 'Cannot prepare report from supplied JSON and context'}]}))
        return 2
    print(json.dumps(prepared, ensure_ascii=True, indent=2, allow_nan=False))
    return 0 if prepared['report']['content']['assessment']['verification'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
