"""Synthetic staged replay package harness, stdout-only; no persistence or outbound export."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from json_input import load_json
from qa_core.application import stage_report_package, check_report_package
from qa_core.reports import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path, help='Caller-held frozen input, also used as check anchor')
    parser.add_argument('assessment', type=Path, help='Caller-held frozen assessment')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--report-id', required=True)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    try:
        bundle, assessment = load_json(args.bundle), load_json(args.assessment)
        context = {'run_id': args.run_id, 'report_id': args.report_id}
        if args.check:
            errors = check_report_package(load_json(args.check), expected_bundle_sha256=digest(bundle),
                                          expected_assessment_sha256=digest(assessment), **context)
            output = {'processingStatus': 'input_error' if errors else 'package_validated', 'errors': errors}
            code = 2 if errors else 0
        else:
            output = stage_report_package(bundle, assessment, **context)
            code = 0 if output['payloads']['prepared']['report']['content']['assessment']['verification'] == 'complete' else 1
        encoded = json.dumps(output, ensure_ascii=True, indent=2, allow_nan=False)
    except (OSError, ValueError, UnicodeError, RecursionError):
        print(json.dumps({'processingStatus': 'input_error', 'errors': [
            {'code': 'E_INPUT', 'message': 'Cannot package or replay supplied JSON and context'}]}))
        return 2
    print(encoded)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
