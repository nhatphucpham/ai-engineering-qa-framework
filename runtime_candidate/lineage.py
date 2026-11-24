"""Trusted fixed-fixture metadata projection; never a general log sanitizer."""
from .common import digest, require, sha, strict_json


def report_lineage(bundle, sources):
    project = bundle['runs'][0]['projectId']
    artifacts = {a['id']: a for a in bundle['artifacts'] if a['projectId'] == project}
    safe = [aid for aid in artifacts if sources[aid][1] == 'safe_source']
    restricted = set(artifacts) - set(safe)
    if not restricted:
        return {'profile': 'all_target_sources_safe_v1', 'sourceIds': sorted(safe)}
    # Raw execution traces/context remain private. Only the existing fixed check outcome
    # schema is allowed to influence derived metadata after reconstructing all offered pins.
    require(restricted == {'vf1-execution-record', 'vf1-coverage-policy'}, 'E_DENIED')
    require(all(sources[aid][1] == 'restricted' for aid in restricted), 'E_DENIED')
    from spikes.vf1.core_bridge import validate_job
    from spikes.vf1.run_vf1 import build_job, OMITTED
    raw_record = sources['vf1-execution-record'][0]
    job = strict_json(sources['vf1-coverage-policy'][0])
    record = strict_json(raw_record)
    validate_job(job, digest(job))
    require(job['executionSha256'] == sha(raw_record) and record['runId'] == job['runId'] == bundle['runs'][0]['id']
            and record['jobId'] == job['jobId'] and record['status'] == 'complete', 'E_INTEGRITY')
    withheld = record['ingestionIntervention']['withheldTestIds']
    require(withheld in ([], [OMITTED]) and record['ingestionIntervention']['appliedBeforeHostRequest'] is True, 'E_INTEGRITY')
    payloads = {}
    for item in job['artifacts']:
        require(item['id'] in safe and sources[item['id']][0] == item['text'].encode('utf-8'), 'E_INTEGRITY')
        payloads['case/' + item['relativePath']] = sources[item['id']][0]
    require(build_job(record, sha(raw_record), withheld, payloads) == job, 'E_INTEGRITY')
    observations = {item['id']: item for item in job['observations']}
    for evidence in bundle['evidence']:
        if evidence['projectId'] != project:
            continue
        observation = observations.get(evidence['id'])
        require(observation is not None and evidence['checkId'] == observation['testId']
                and evidence['outcome'] == observation['outcome'] and evidence['level'] == observation['level']
                and evidence['executionRef'] == job['executionRef'] and evidence['revision'] == job['candidateRevision'], 'E_INTEGRITY')
    return {'profile': 'vf1_fixed_outcome_metadata_v1', 'sourceIds': sorted(safe),
            'restrictedOrigins': sorted(restricted), 'executionDigest': sha(raw_record),
            'jobDigest': digest(job), 'allowedDerivedKinds': ['check_outcome', 'core_status', 'core_reason', 'core_action']}
