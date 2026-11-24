"""Context mapping tests use historical bytes; they never claim new execution or reasoning."""
from copy import deepcopy
from pathlib import Path
import unittest

from .common import digest, strict_json
from .execution_projection import project
from .publication import prepare

BASE = Path(__file__).resolve().parents[1] / 'docs/hc1-results/hc1-20261118-live-r3/a'


class ExecutionProjectionTest(unittest.TestCase):
    def test_attempt_job_stays_distinct_from_held_handoff_and_policy(self):
        job = strict_json((BASE / 'host-request.json').read_bytes())
        response = strict_json((BASE / 'native-response-2.json').read_bytes())
        before = digest(job), digest(response)
        held = {'projectId': 'candidateProject', 'taskRef': 'candidateTask', 'runId': job['runId'],
                'handoffId': 'candidateHandoff', 'projectConfigVersion': 2, 'dataPolicyVersion': 3,
                'candidateRevision': job['candidateRevision'], 'requirementVersion': job['requirementVersion']}
        result = project(job, response, held)
        prepared = prepare(result['bundle'], result['assessment'], expected_bundle_digest=digest(result['bundle']),
                           expected_assessment_digest=digest(result['assessment']), run_id=job['runId'], report_id='report')
        for key, value in held.items():
            self.assertEqual(prepared.package['target'][key], value)
        self.assertEqual(before, (digest(job), digest(response)))
        self.assertEqual(result['origin']['jobId'], job['jobId'])
        self.assertNotEqual(result['origin']['jobId'], prepared.package['target']['handoffId'])
        artifacts = {row['id']: row for row in result['bundle']['artifacts']}
        self.assertEqual({a['id']: a['sha256'] for a in job['artifacts']},
                         {a['id']: artifacts[a['id']]['sha256'] for a in job['artifacts']})
        self.assertEqual(prepared.view['humanDecision'], 'pending')


if __name__ == '__main__':
    unittest.main()
