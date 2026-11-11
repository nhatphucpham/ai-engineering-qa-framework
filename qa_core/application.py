"""Headless application boundary shared by future clients; no I/O or live enforcement."""

from .runtime import propose_completion, validate_completion
from .publication import create_publication_package, validate_publication_package


def prepare_report(bundle, assessment, *, run_id, report_id):
    """Prepare versioned internal report and completion intent over supplied judgments."""
    return propose_completion(bundle, assessment, run_id, report_id)


def check_prepared_report(prepared, bundle, assessment, *, run_id, report_id):
    return validate_completion(prepared, bundle, assessment, run_id, report_id)


def stage_report_package(bundle, assessment, *, run_id, report_id):
    return create_publication_package(bundle, assessment, run_id=run_id, report_id=report_id)


def check_report_package(package, *, expected_bundle_sha256, expected_assessment_sha256, run_id, report_id):
    return validate_publication_package(package, expected_bundle_sha256=expected_bundle_sha256,
                                        expected_assessment_sha256=expected_assessment_sha256,
                                        run_id=run_id, report_id=report_id)
