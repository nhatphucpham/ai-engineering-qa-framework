"""Actual PostgreSQL dump/restore and TLS cutover, run serially by the campaign owner."""
from contextlib import closing, contextmanager
from pathlib import Path
import threading
import uuid

from qa_core.application import check_report_package

from .application import Application
from .blobs import MAX_BLOB_BYTES
from .checkpoint import backup, restore
from .common import VERSION, Error, digest, require, strict_json
from .transport import CandidateClient, serve


def denied(function):
    try:
        function()
    except Error as exc:
        require(exc.code == 'E_UNRESOLVED', 'E_INTEGRITY')
        return
    raise AssertionError('Untrusted restore authority accepted')


@contextmanager
def listener(ctx, schema, root):
    server = serve(lambda: Application(schema, root), ctx['certificate'], ctx['private_key'])
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    client = CandidateClient('127.0.0.1', server.server_address[1], ctx['certificate'])
    try:
        yield client
    finally:
        server.shutdown(); server.server_close(); thread.join(5)
        require(not thread.is_alive(), 'E_DEPENDENCY')


def request(client, op, token, **params):
    return client.call(op, token, dict(params, version=VERSION))


def _private_report(app, project, run_id):
    row = app.conn.execute('''SELECT project,run_id,report_id,private_ref,bundle_digest,assessment_digest
        FROM rt_reports WHERE project=%s AND run_id=%s''', (project, run_id)).fetchone()
    require(row is not None, 'E_INTEGRITY')
    return row, app.blobs.get(row['private_ref'])


def run_cases(ctx):
    checks = ctx.get('checks', {})
    workspace, project, run_id = ctx['workspace'], ctx['project'], ctx['run_id']
    with closing(ctx['factory']()) as source:
        old_archive = workspace / 'backup_before_authority_change'
        old_receipt = backup(source.store, old_archive)
        current = ctx['call']('project_read', ctx['admin'], project=project)
        ctx['call']('grant_issue', ctx['admin'], project=project, actions=['read'], expected_config=current['configVersion'])
        stale_root = workspace / 'stale_restore'
        stale_schema = 'id_' + uuid.uuid4().hex
        denied(lambda: restore(source.store, old_archive, checkpoint=old_receipt, target_schema=stale_schema, target_root=stale_root))
        require(not stale_root.exists() and not source.conn.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s) AS present',
                                                                  (stale_schema,)).fetchone()['present'], 'E_INTEGRITY')
        archive = workspace / 'backup_current'
        receipt = backup(source.store, archive)
        missing_root = workspace / 'missing_pin_restore'
        denied(lambda: restore(source.store, archive, checkpoint={}, target_schema='id_' + uuid.uuid4().hex, target_root=missing_root))
        require(not missing_root.exists(), 'E_INTEGRITY')
        maintenance_schema, maintenance_root = 'id_' + uuid.uuid4().hex, workspace / 'maintenance_restore'
        maintenance = restore(source.store, archive, checkpoint=receipt, target_schema=maintenance_schema, target_root=maintenance_root)
        require(maintenance['state'] == 'verified_maintenance', 'E_INTEGRITY')
        with listener(ctx, maintenance_schema, maintenance_root) as client:
            denied(lambda: request(client, 'session_read', ctx['admin']))
        checks['I16'] = {'status': 'PASS', 'actualPgDumpAndPsqlRestore': True, 'staleAuthorityBeforeWritesDenied': True,
                         'missingIndependentPinDenied': True, 'maintenanceTlsCannotServe': True,
                         'blobCount': receipt['blobCount'], 'mode': 'operator_online_source_only'}
        expected = ctx['call']('report_read', ctx['admin'], project=project, run_id=run_id)
        with source.store.unit():
            run = source.store.run(project, run_id)
            issuer = source.conn.execute('''SELECT bundle_digest,assessment_digest FROM rt_assessments
                WHERE project=%s AND run_id=%s AND assignment=%s''', (project, run_id, run['assignment'])).fetchone()
            snapshot = source.store.snapshot(project, run['snapshot'])
            target = dict(snapshot['manifest']['coreTarget'], reportId='report_' + run_id)
            original_row, original_bytes = _private_report(source, project, run_id)
            require(issuer is not None
                    and issuer == {'bundle_digest': digest(ctx['dataA']['bundle']),
                                   'assessment_digest': digest(ctx['dataA']['assessment'])}
                    and (original_row['bundle_digest'], original_row['assessment_digest']) ==
                    (issuer['bundle_digest'], issuer['assessment_digest'])
                    and (target['projectId'], target['runId'], target['reportId']) ==
                    (project, run_id, expected['reportId'])
                    and original_row['report_id'] == target['reportId'] and run['state'] == 'completed', 'E_INTEGRITY')
        target_schema, target_root = 'id_' + uuid.uuid4().hex, workspace / 'active_restore'
        result = restore(source.store, archive, checkpoint=receipt, target_schema=target_schema, target_root=target_root, activate=True)
        require(result['state'] == 'active_restore', 'E_INTEGRITY')
        denied(lambda: ctx['call']('report_read', ctx['admin'], project=project, run_id=run_id))
    with listener(ctx, target_schema, target_root) as client:
        restored = request(client, 'report_read', ctx['admin'], project=project, run_id=run_id)
        require(restored == expected, 'E_INTEGRITY')
        events = client.events(project, run_id, ctx['admin'], after=0)
        require(len([row for row in events if row['event'] == 'report_ready']) == 1, 'E_INTEGRITY')
        from local import start, read_config
        from .database import stop_database
        config = read_config(False)
        before_pid = (Path(config['data']) / 'postmaster.pid').read_text().splitlines()[0]
        stopped = stop_database(); start()
        after_pid = (Path(config['data']) / 'postmaster.pid').read_text().splitlines()[0]
        require(after_pid != before_pid and request(client, 'report_read', ctx['admin'], project=project, run_id=run_id) == expected,
                'E_INTEGRITY')
        require(client.events(project, run_id, ctx['admin'], after=events[-1]['id']) == [], 'E_INTEGRITY')
        with closing(Application(target_schema, target_root)) as app, app.store.unit():
            restored_row, restored_bytes = _private_report(app, project, run_id)
            require(restored_row == original_row and restored_bytes == original_bytes, 'E_INTEGRITY')
            package = strict_json(restored_bytes, MAX_BLOB_BYTES)
            require(package['target'] == target
                    and not check_report_package(package, expected_bundle_sha256=issuer['bundle_digest'],
                                                 expected_assessment_sha256=issuer['assessment_digest'],
                                                 run_id=run_id, report_id=target['reportId']), 'E_INTEGRITY')
        checks['I17'] = {'status': 'PASS', 'exclusiveCutoverOldTlsAuthorityDenied': True,
                         'restoredTlsReportAndSourceLinksExact': True, 'actualDatabaseRestart': True,
                         'postgresPidBefore': int(before_pid), 'postgresPidAfter': int(after_pid),
                         'maintenanceStop': stopped,
                         'restoredPrivatePackageReferenceAndBytesExact': True,
                         'restoredPrivatePackageCoreReplayAgainstOriginalIssuerPins': True,
                         'privatePackageReference': original_row['private_ref'], 'issuerInputDigests': issuer,
                         'oneReportReadyAfterRestoreAndRestart': True, 'lostSourceDisasterRecovery': 'not claimed'}
    return checks
