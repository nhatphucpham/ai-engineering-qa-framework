"""Recovery-ready fixed QA entry; no unbound executor or artifact-supplied command."""
from .common import require


def execute(output, staging, run_id, job_id, held_input_hashes, check_authority, *,
            controller, worker_token, body, admission, after_live=None):
    from spikes.vf1.core_bridge import ARTIFACT_KINDS
    from spikes.m50_worker.qa_executor import execute_qa
    expected = {'case/' + path for path in ARTIFACT_KINDS} | {'test_worker.py'}
    require(isinstance(held_input_hashes, dict) and set(held_input_hashes) == expected, 'E_INTEGRITY')
    return execute_qa(output, staging, run_id, job_id, held_input_hashes, check_authority,
                      controller=controller, worker_token=worker_token, body=body, admission=admission,
                      after_live=after_live)
