"""Versioned context adapter: preserve observed bytes while binding current issuer context."""
from copy import deepcopy

from .common import digest, require

VERSION = 'm50-vf1-context-1.0.0'


def project(job, proposal, held):
    """The server supplies held project/task/handoff/config identities, never the model.

    This does not edit historical inputs or execution. It constructs NEW versioned core
    inputs; raw job/jobId, source hashes, observations and execution reference stay intact.
    """
    from spikes.vf1.core_bridge import validate_job, response_assessment, contract_bundle
    require(job['runId'] == held['runId'], 'E_INTEGRITY')
    artifacts, requirement, observations, _ = validate_job(job, digest(job))
    assessment = response_assessment(job, proposal, digest(job), artifacts, observations)
    bundle = contract_bundle(job, assessment, artifacts, requirement, observations)
    bundle, assessment = deepcopy(bundle), deepcopy(assessment)
    for row in bundle['projects']:
        row['id'] = held['projectId']; row['configVersion'] = held['projectConfigVersion']
        row['dataPolicy']['version'] = held['dataPolicyVersion']
    for key in ('tasks', 'artifacts', 'handoffs', 'evidence', 'runs', 'commands', 'memberships'):
        for row in bundle[key]:
            row['projectId'] = held['projectId']
            if key == 'tasks':
                row['id'] = held['taskRef']
            if 'taskRef' in row:
                row['taskRef'] = held['taskRef']
            if 'handoffId' in row:
                row['handoffId'] = held['handoffId']
            if key == 'handoffs':
                row['id'] = held['handoffId']
            if key == 'runs':
                row['projectConfigVersion'] = held['projectConfigVersion']
                row['dataPolicyVersion'] = held['dataPolicyVersion']
            if key == 'commands':
                for field in ('taskRef', 'handoffId', 'projectConfigVersion', 'dataPolicyVersion'):
                    if field in row['payload']:
                        row['payload'][field] = held[field]
    assessment.update(projectId=held['projectId'], handoffId=held['handoffId'],
                      projectConfigVersion=held['projectConfigVersion'], dataPolicyVersion=held['dataPolicyVersion'])
    require(bundle['runs'][0]['candidateRevision'] == held['candidateRevision'] and
            bundle['handoffs'][0]['requirementVersion'] == held['requirementVersion'], 'E_INTEGRITY')
    return {'version': VERSION, 'bundle': bundle, 'assessment': assessment,
            'origin': {'jobId': job['jobId'], 'jobDigest': digest(job), 'executionSha256': job['executionSha256']},
            'heldContext': deepcopy(held)}
