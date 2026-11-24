"""Pure candidate operation and read contracts; no runtime/dependency discovery."""

FIELDS = {
    'session_login': 'user password', 'session_refresh': 'refresh', 'session_read': '', 'session_logout': '',
    'session_change_password': 'old new', 'account_create': 'user password',
    'account_set_enabled': 'user enabled', 'account_set_role': 'project user role', 'account_reset_password': 'user password',
    'project_create': 'project owner', 'project_list': '', 'project_read': 'project',
    'project_configure': 'project expected_config config', 'grant_issue': 'project actions expected_config',
    'grant_revoke': 'project grant', 'service_enroll': 'service kind projects', 'service_revoke': 'service',
    'intake_snapshot': 'project key kind snapshot_ref candidate_digest input_digest expected_config',
    'run_start': 'project key run_id intake_id grant expected_config',
    'run_cancel': 'project key run_id grant expected_version', 'run_list': 'project',
    'run_read': 'project run_id', 'report_read': 'project run_id', 'source_read': 'project run_id artifact_id',
    'report_export': 'project run_id', 'events': 'project run_id after',
    'worker_claim': 'project worker expected_run_version run_id',
    'worker_recover_claim': 'project worker expected_run_version run_id',
    'worker_renew': 'project run_id assignment fence lease_token',
    'worker_admit': 'project run_id assignment fence lease_token',
    'worker_observe_cleanup': 'project run_id assignment fence lease_token',
    'worker_submit': 'project run_id assignment fence lease_token assessment_digest',
    'worker_fail': 'project run_id assignment fence lease_token code',
    'collector_record': 'project run_id assignment fence effect_nonce execution cleanup',
    'assessment_accept': 'project run_id assignment fence effect_nonce bundle assessment bundle_digest assessment_digest execution_digest',
}
READ_ACTION = {'session_read': None, 'project_list': None, 'project_read': 'read', 'run_list': 'read',
               'run_read': 'read', 'report_read': 'report', 'source_read': 'source', 'report_export': 'export', 'events': 'stream'}


def safe_run(row):
    return {'project': row['project'], 'runId': row['id'], 'state': row['state'], 'stateVersion': row['version'],
            'sequenceWatermark': row['sequence'], 'attempt': row['attempt'], 'incidentOpen': row['incident'],
            'humanDecision': 'pending'}

