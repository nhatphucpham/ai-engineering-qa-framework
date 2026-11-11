"""S2-B actual PostgreSQL races/faults. New namespaces and evidence, no mock DB."""

from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import traceback
import uuid

from store_b import LeaseStore, Rejected, ROOT, digest, psycopg
from local import CACHE, inventory, stop, start
from run import require, reject


def fresh(store, name, ttl_ms=1800000, receipt=True):
    store.seed(name)
    claim = store.claim(name, ttl_ms=ttl_ms)
    package = store.package(claim)
    if receipt:
        store.accept_receipt(claim, package)
    return claim, package


def wait_due(store, run_id, column='expires'):
    require(column in ('expires', 'cleanup_deadline'), 'Invalid test clock field')
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        if store.conn.execute(f'SELECT {column}<=clock_timestamp() AS due FROM runs WHERE id=%s',
                               (run_id,)).fetchone()['due']:
            return
        time.sleep(0.01)
    raise AssertionError('DB clock deadline was not reached')


def observation(store, run_id, request_id):
    request = store.conn.execute('SELECT * FROM cleanup_requests WHERE id=%s', (request_id,)).fetchone()
    return {'run_id': run_id, 'request_id': request_id, 'attempt': request['attempt'], 'fence': request['fence'],
            'observation': {'kind': 'synthetic-cleanup-observation', 'runId': run_id, 'requestId': request_id,
                'attempt': request['attempt'], 'fence': request['fence'], 'observationId': 'observed-' + uuid.uuid4().hex}}


def expired(store, name, cleanup_ms=1800000):
    claim, package = fresh(store, name, ttl_ms=350)
    wait_due(store, name)
    request = store.reconcile_expired(name, cleanup_ms=cleanup_ms)
    require(request is not None, 'Recovery request missing')
    return claim, package, observation(store, name, request)


def race_process(schema, actions, barrier, output):
    results = []
    def worker(action):
        store = None
        try:
            store = LeaseStore(schema)
            backend = store.conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
            barrier.wait(timeout=20)
            begin = time.time_ns()
            try:
                value = getattr(store, action['op'])(**action['args'])
                status = 'empty' if value is None and action['op'] in ('claim', 'reconcile_expired') else 'accepted'
                result = {'status': status, 'value': value.isoformat() if isinstance(value, datetime) else value}
            except (Rejected, psycopg.errors.UniqueViolation):
                result = {'status': 'rejected'}
            results.append({'op': action['op'], 'backend': backend, 'process': mp.current_process().pid,
                            'begin_ns': begin, 'end_ns': time.time_ns(), **result})
        except Exception as error:
            results.append({'op': action['op'], 'status': 'ERROR', 'errorType': type(error).__name__})
        finally:
            if store:
                store.close()
    threads = [threading.Thread(target=worker, args=(action,)) for action in actions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(35)
    output.send(results)
    output.close()


def race(schema, actions):
    require(len(actions) in (2, 4), 'Race needs 2 or 4 independent connections')
    barrier = mp.Barrier(len(actions))
    children, pipes = [], []
    for batch in (actions[:len(actions)//2], actions[len(actions)//2:]):
        parent, child = mp.Pipe()
        proc = mp.Process(target=race_process, args=(schema, batch, barrier, child))
        proc.start()
        child.close()
        children.append(proc)
        pipes.append(parent)
    try:
        results = []
        for pipe in pipes:
            require(pipe.poll(45), 'Race process timeout')
            results.extend(pipe.recv())
        for proc in children:
            proc.join(10)
            require(proc.exitcode == 0, 'Race process exit failed')
        require(len(results) == len(actions) and all(r['status'] != 'ERROR' for r in results),
                'Race connection error: ' + str(results))
        require(len({r['backend'] for r in results}) == len(actions) and len({r['process'] for r in results}) == 2,
                'Independent race process/connection inventory incomplete')
        return results
    finally:
        for proc in children:
            if proc.is_alive():
                proc.kill()
                proc.join(10)
        for pipe in pipes:
            pipe.close()


def op(name, **args):
    return {'op': name, 'args': args}


def recovery_child(schema, run_id, pipe):
    store = LeaseStore(schema)
    def paused():
        pipe.send('recovery_written_uncommitted')
        pipe.recv()
    store.reconcile_expired(run_id, hook=paused)
    store.close()


def experiment(evidence):
    schema = 's2_' + uuid.uuid4().hex
    evidence['schema'] = schema
    store = LeaseStore(schema, create=True)
    checks = evidence['checks'] = {}
    try:
        evidence['database'] = store.conn.execute('''SELECT version() AS version,current_setting('fsync') AS fsync,
            current_setting('synchronous_commit') AS synchronous_commit,current_setting('full_page_writes') AS full_page_writes''').fetchone()
        require(all(evidence['database'][k] == 'on' for k in ('fsync','synchronous_commit','full_page_writes')), 'Unsafe DB settings')
        c, p = fresh(store, 'renew')
        before = store.snapshot(c['id'])
        row = store.row(c['id'])
        expiry = row['expires']
        anchors = [row['bundle_sha'], row['assessment_sha'], digest(p)]
        new_expiry = store.renew(c)
        require(new_expiry >= expiry and store.snapshot(c['id']) == before, 'Renew changed version/attempt/fence/state')
        row = store.row(c['id'])
        require(anchors == [row['bundle_sha'], row['assessment_sha'], digest(store.package(c))], 'Renew changed frozen package')
        require(store.renew(c, ttl_ms=50) >= new_expiry, 'Renew shortened lease')
        store.complete(c, p)
        checks['B01'] = {'status': 'PASS', 'before': before, 'expiry_before': expiry.isoformat(),
            'expiry_after': new_expiry.isoformat(), 'after': store.snapshot(c['id']), 'roundtrip': store.verify_roundtrip(c,p)}

        c, p = fresh(store, 'stale', ttl_ms=350, receipt=False)
        for key in ('version','attempt','fence'):
            bad = {**c, key: c[key]-1}
            reject(lambda: store.renew(bad))
            reject(lambda: store.accept_receipt(bad,p))
            reject(lambda: store.complete(bad,p))
        wait_due(store,c['id'])
        before = store.snapshot(c['id'])
        for action in (lambda: store.renew(c),lambda: store.accept_receipt(c,p),lambda: store.complete(c,p)):
            reject(action)
        require(store.snapshot(c['id']) == before, 'Expired request changed run')
        crossing=[]
        for method in ('renew','accept_receipt','complete'):
            dc,dp=fresh(store,'cross-expiry-'+method,ttl_ms=1000,receipt=(method=='complete'))
            dbefore=store.snapshot(dc['id'])
            called=[]
            def delay():
                called.append(True)
                wait_due(store,dc['id'])
            if method=='renew':
                reject(lambda:store.renew(dc,before_write=delay))
            else:
                reject(lambda:getattr(store,method)(dc,dp,before_write=delay))
            require(called==[True] and store.snapshot(dc['id'])==dbefore,'Cross-expiry write was not rejected atomically')
            crossing.append({'method':method,'delay_hook_reached':True,'state':dbefore})
        checks['B02'] = {'status':'PASS','probes':'wrong version/attempt/fence + expired renew/receipt/complete',
                         'state':before,'expiry_between_check_and_write':crossing}

        c1, p1, ack = expired(store,'reclaim')
        pending = store.snapshot(c1['id'])
        require(pending['state']=='recovering' and pending['open_incidents']==1 and pending['requests']==1,'Recovery not persisted')
        require(store.reconcile_expired(c1['id']) is None,'Recovery duplicated')
        blocked = race(schema,[op('claim',specific=c1['id']) for _ in range(4)])
        require(all(r['status']=='empty' for r in blocked),'Claim bypassed pending cleanup')
        for key in ('attempt','fence','request_id','run_id'):
            bad = dict(ack)
            bad[key] = bad[key]+1 if isinstance(bad[key],int) else bad[key]+'-wrong'
            reject(lambda: store.ack_cleanup(**bad))
        reject(lambda: store.ack_cleanup(**{**ack,'observation':True}))
        for key in ('attempt','fence'):
            for value in (True,float(ack[key])):
                bad=dict(ack); bad[key]=value
                reject(lambda:store.ack_cleanup(**bad))
                bad={**ack,'observation':{**ack['observation'],key:value}}
                reject(lambda:store.ack_cleanup(**bad))
        require(store.snapshot(c1['id'])==pending,'Invalid cleanup acknowledgement mutated run')
        require(store.ack_cleanup(**ack)=='queued','Cleanup did not permit queued retry')
        reject(lambda: store.ack_cleanup(**ack))
        winners = race(schema,[op('claim',specific=c1['id']) for _ in range(4)])
        accepted = [r for r in winners if r['status']=='accepted']
        require(len(accepted)==1 and sum(r['status']=='empty' for r in winners)==3,'Duplicate reclaim')
        c2=accepted[0]['value']
        require(c2['attempt']==2 and c2['version']>c1['version'] and c2['fence']>c1['fence'],'Retry fencing did not advance')
        first=store.conn.execute('SELECT * FROM attempt_inputs WHERE run_id=%s AND attempt=1',(c1['id'],)).fetchone()
        require(bytes(first['bundle']) == canonical_bytes(p1['payloads']['bundle']),'Prior canonical input overwritten')
        require(first['bundle_sha']==digest(p1['payloads']['bundle']),'Prior anchor lost')
        checks['B03']={'status':'PASS','pending':pending,'invalid_ack_probes':['attempt','fence','request','run','boolean','numeric_boolean_or_float','replay'],
                       'after':store.snapshot(c1['id']),'prior_bundle_sha':first['bundle_sha']}
        checks['B05']={'status':'PASS','blocked_before_ack':blocked,'after_ack_reclaim':winners}

        p2=store.package(c2)
        for action in (lambda:store.renew(c1),lambda:store.accept_receipt(c1,p1),lambda:store.complete(c1,p1),
                       lambda:store.complete(c2,p1),lambda:store.complete(c2,p2)):
            reject(action)
        store.accept_receipt(c2,p2)
        store.complete(c2,p2)
        require(store.snapshot(c1['id'])['receipts']==2,'Attempt receipt history lost')
        checks['B04']={'status':'PASS','stale_attempt':c1,'current_attempt':c2,'state':store.snapshot(c1['id']),
                       'roundtrip':store.verify_roundtrip(c2,p2)}

        stop_results=[]
        for reason in ('cancel','revoke'):
            c,p=fresh(store,'stop-first-'+reason)
            request=store.request_stop(c['id'],c['version'],reason)
            cancelling=store.snapshot(c['id'])
            require(cancelling['state']=='cancelling' and cancelling['reports']==cancelling['outbox']==0,'Stop skipped cancelling')
            for action in (lambda:store.renew(c),lambda:store.accept_receipt(c,p),lambda:store.complete(c,p),lambda:store.cancel_predicate(c)):
                reject(action)
            require(store.claim(c['id']) is None,'Stop permitted new attempt')
            require(store.ack_cleanup(**observation(store,c['id'],request))=='cancelled','Cancelled before/without cleanup')
            terminal=store.snapshot(c['id'])
            reject(lambda:store.request_stop(c['id'],terminal['version'],reason))
            require(store.snapshot(c['id'])==terminal,'Terminal stop mutated row')
            c,p=fresh(store,'complete-first-'+reason)
            store.complete(c,p)
            completed=store.snapshot(c['id'])
            reject(lambda:store.request_stop(c['id'],completed['version'],reason))
            require(store.snapshot(c['id'])==completed,'Stop mutated completed run')
            c,p=fresh(store,'race-stop-'+reason)
            results=race(schema,[op('complete',claim=c,package=p),op('request_stop',run_id=c['id'],expected_version=c['version'],reason=reason)])
            require(sum(r['status']=='accepted' for r in results)==1,'Complete/stop race did not have one winner')
            row=store.snapshot(c['id'])
            require(row['reports']==row['outbox']==int(row['state']=='completed'),'Partial race publication')
            if row['state']=='cancelling':
                store.ack_cleanup(**observation(store,c['id'],row['cleanup_request']))
            stop_results.append({'reason':reason,'ordered_cancelled':terminal,'ordered_completed':completed,
                                  'race':results,'race_after_cleanup':store.snapshot(c['id'])})
        checks['B06']={'status':'PASS','observations':stop_results,'authenticatedRevoke':'NOT RUN','containerCleanup':'NOT RUN'}

        c,p,ack=expired(store,'timeout',cleanup_ms=1000)
        reject(lambda:store.cleanup_timeout(c['id']))
        wait_due(store,c['id'],'cleanup_deadline')
        store.cleanup_timeout(c['id'])
        failed=store.snapshot(c['id'])
        require(failed['state']=='failed' and failed['terminal_reason']=='cleanup_unconfirmed' and failed['open_incidents']==1,'Timeout falsely clean/cancelled')
        run_before=dict(store.row(c['id']))
        store.ack_cleanup(**ack)
        run_after=dict(store.row(c['id']))
        # row() includes live unexpired expression (NULL here); terminal bytes/columns must match.
        require(run_before==run_after and store.snapshot(c['id'])['open_incidents']==0,'Late cleanup mutated terminal run')
        require(store.claim(c['id']) is None,'Late cleanup reopened failed run')
        c,p,ack=expired(store,'late-ack-no-sweeper',cleanup_ms=100)
        wait_due(store,c['id'],'cleanup_deadline')
        require(store.ack_cleanup(**ack)=='failed','Late acknowledgement bypassed deadline without sweeper')
        c,p,ack=expired(store,'ack-timeout-race',cleanup_ms=100)
        wait_due(store,c['id'],'cleanup_deadline')
        results=race(schema,[op('ack_cleanup',**ack),op('cleanup_timeout',run_id=c['id'])])
        require(store.snapshot(c['id'])['state']=='failed','Deadline race resurrected run')
        checks['B07']={'status':'PASS','failed_before_late_ack':failed,'late_ack_terminal_immutable':run_before==run_after,
                       'deadline_race':results,'race_after':store.snapshot(c['id'])}

        c,p,ack=expired(store,'budget')
        store.ack_cleanup(**ack)
        c=store.claim(c['id'],ttl_ms=150)
        wait_due(store,c['id'])
        request=store.reconcile_expired(c['id'])
        require(store.ack_cleanup(**observation(store,c['id'],request))=='failed','Budget failed to bound attempts')
        require(store.claim(c['id']) is None and store.snapshot(c['id'])['attempt']==2,'Attempt3 accepted')
        checks['B08']={'status':'PASS','state':store.snapshot(c['id'])}

        # Uncommitted recovery must not partially survive DB crash; committed request must survive it.
        c,p,committed_ack=expired(store,'committed-recovery')
        committed_before=store.snapshot(c['id'])
        crash_c,crash_p=fresh(store,'uncommitted-recovery',ttl_ms=350)
        wait_due(store,crash_c['id'])
        before=store.snapshot(crash_c['id'])
        parent,child=mp.Pipe()
        proc=mp.Process(target=recovery_child,args=(schema,crash_c['id'],child))
        proc.start(); child.close()
        try:
            require(parent.poll(20) and parent.recv()=='recovery_written_uncommitted','Recovery fault point missing')
            require(store.snapshot(crash_c['id'])==before,'Uncommitted recovery exposed')
            store.close()
            stop('immediate')
            proc.terminate(); proc.join(10)
            require(not proc.is_alive() and proc.exitcode!=0,'Recovery child kill failed')
            start()
        finally:
            if proc.is_alive(): proc.kill(); proc.join(10)
            parent.close()
        store=LeaseStore(schema)
        committed_recovered=store.snapshot('committed-recovery')
        uncommitted_recovered=store.snapshot(crash_c['id'])
        require(committed_recovered==committed_before,'Committed recovery request lost')
        require(uncommitted_recovered==before,'Partial uncommitted recovery survived')
        request=store.reconcile_expired(crash_c['id'])
        require(request is not None and store.reconcile_expired(crash_c['id']) is None,'Restart reconcile not idempotent')
        require(store.claim(crash_c['id']) is None and store.claim('committed-recovery') is None,'Restart bypassed cleanup')
        store.ack_cleanup(**observation(store,crash_c['id'],request))
        store.ack_cleanup(**committed_ack)
        reclaimed=store.claim(crash_c['id'])
        require(reclaimed['attempt']==2,'Restart reclaim attempt mismatch')
        recovery_log=[line for line in (CACHE/'postgres.log').read_text(encoding='utf-8').splitlines()[-30:]
                      if any(message in line for message in ('immediate shutdown','automatic recovery','redo starts','redo done','ready to accept'))]
        require(any('automatic recovery' in line for line in recovery_log),'WAL recovery log missing')
        checks['B09']={'status':'PASS','committed_before':committed_before,'uncommitted_before':before,
            'committed_after_restart':committed_recovered,'uncommitted_after_restart':uncommitted_recovered,
            'after_restart_and_reconcile':store.snapshot(crash_c['id']),'reclaimed':reclaimed,
            'child_exitcode':proc.exitcode,'dbStoppedWithOpenRecoveryTransaction':True,'recovery_log':recovery_log}

        c,p=fresh(store,'renew-vs-reconcile')
        active=race(schema,[op('renew',claim=c),op('reconcile_expired',run_id=c['id'])])
        require(next(r for r in active if r['op']=='renew')['status']=='accepted' and
                next(r for r in active if r['op']=='reconcile_expired')['status']=='empty','Active renewal/reconcile mismatch')
        c,p=fresh(store,'expired-renew-vs-reconcile',ttl_ms=350)
        wait_due(store,c['id'])
        due=race(schema,[op('renew',claim=c),op('reconcile_expired',run_id=c['id'])])
        require(next(r for r in due if r['op']=='renew')['status']=='rejected' and
                next(r for r in due if r['op']=='reconcile_expired')['status']=='accepted','Expired renewal/reconcile mismatch')
        reclaim_races=[]; renewal_races=[]; recovery_races=[]; ordered_opposites=[]
        for reason in ('cancel','revoke'):
            c,p,ack=expired(store,'stop-vs-reclaim-'+reason)
            store.ack_cleanup(**ack)
            queued=store.snapshot(c['id'])
            competing=race(schema,[op('claim',specific=c['id']),op('request_stop',run_id=c['id'],expected_version=queued['version'],reason=reason)])
            require(sum(r['status']=='accepted' for r in competing)==1,'Reclaim/stop CAS has multiple winners')
            for action in (lambda:store.renew(c),lambda:store.accept_receipt(c,p),lambda:store.complete(c,p)):
                reject(action)
            reclaim_races.append({'reason':reason,'race':competing,'state':store.snapshot(c['id'])})
            c,p=fresh(store,'stop-vs-renew-'+reason)
            competing=race(schema,[op('renew',claim=c),op('request_stop',run_id=c['id'],expected_version=c['version'],reason=reason)])
            require(next(r for r in competing if r['op']=='request_stop')['status']=='accepted','Heartbeat invalidated stop version')
            pending=store.snapshot(c['id'])
            require(pending['state']=='cancelling' and pending['reports']==pending['outbox']==0,'Renew bypassed stop')
            reject(lambda:store.renew(c)); reject(lambda:store.complete(c,p))
            store.ack_cleanup(**observation(store,c['id'],pending['cleanup_request']))
            renewal_races.append({'reason':reason,'race':competing,'pending':pending,'after':store.snapshot(c['id'])})
            c,p=fresh(store,'stop-vs-reconcile-'+reason,ttl_ms=350)
            wait_due(store,c['id'])
            competing=race(schema,[op('reconcile_expired',run_id=c['id']),
                op('request_stop',run_id=c['id'],expected_version=c['version'],reason=reason)])
            require(sum(r['status']=='accepted' for r in competing)==1,'Recovery/stop did not serialize CAS')
            observed=store.snapshot(c['id'])
            retried=False
            if observed['state']=='recovering':
                store.request_stop(c['id'],observed['version'],reason)
                retried=True  # Explicit one retry after refreshed CAS context, not silent success.
            pending=store.snapshot(c['id'])
            require(pending['state']=='cancelling' and pending['requests']==1,'Recovery/stop duplicated cleanup request')
            require(store.claim(c['id']) is None,'Recovery/stop bypassed cleanup')
            store.ack_cleanup(**observation(store,c['id'],pending['cleanup_request']))
            recovery_races.append({'reason':reason,'race':competing,'observed':observed,
                                  'explicit_refreshed_version_retry':retried,'after':store.snapshot(c['id'])})
            # Force opposite orders as well: scheduler winners above are observations, not coverage guarantees.
            oc,opackage,oack=expired(store,'ordered-recovery-first-'+reason)
            recovery_first=store.snapshot(oc['id'])
            reject(lambda:store.request_stop(oc['id'],oc['version'],reason))
            reused=store.request_stop(oc['id'],recovery_first['version'],reason)
            require(reused==oack['request_id'],'Recovery-first stop replaced cleanup identity')
            store.ack_cleanup(**oack)
            recovery_terminal=store.snapshot(oc['id'])
            oc,opackage,oack=expired(store,'ordered-reclaim-first-'+reason)
            store.ack_cleanup(**oack)
            qversion=store.snapshot(oc['id'])['version']
            newer=store.claim(oc['id'])
            reject(lambda:store.request_stop(oc['id'],qversion,reason))
            request=store.request_stop(oc['id'],newer['version'],reason)
            store.ack_cleanup(**observation(store,oc['id'],request))
            reclaimed_terminal=store.snapshot(oc['id'])
            oc,opackage=fresh(store,'ordered-renew-first-'+reason)
            store.renew(oc)
            request=store.request_stop(oc['id'],oc['version'],reason)
            store.ack_cleanup(**observation(store,oc['id'],request))
            ordered_opposites.append({'reason':reason,'recovery_first':recovery_first,
                'recovery_then_stop':recovery_terminal,'reclaim_then_refreshed_stop':reclaimed_terminal,
                'renew_then_stop':store.snapshot(oc['id'])})
        checks['B10']={'status':'PASS','active':active,'expired':due,'stop_vs_reclaim':reclaim_races,
                       'stop_vs_renew':renewal_races,'stop_vs_expiry_reconcile':recovery_races,
                       'ordered_opposite_cases':ordered_opposites}
    finally:
        store.close()


def canonical_bytes(value):
    from store import canonical
    return canonical(value)


def inputs():
    paths=set()
    for folder in ('qa_core','schemas','spikes/s2','spikes/s2b','examples/reports/runtime-v1'):
        paths.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.add(ROOT/'docs/S2-B-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv)!=2: raise SystemExit('Usage: py -3 -B spikes/s2b/run_b.py docs/s2b-results/<new-id>.json')
    destination=(ROOT/sys.argv[1]).resolve()
    if destination.parent!=(ROOT/'docs/s2b-results').resolve() or destination.suffix!='.json' or destination.exists():
        raise SystemExit('Use a new evidence destination under docs/s2b-results')
    evidence={'evidenceVersion':'s2-b-1.0.0','classification':'synthetic-only',
        'baseline':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'startedAt':datetime.now(timezone.utc).isoformat(),'command':'py -3 -B spikes/s2b/run_b.py '+sys.argv[1],
        'environment':{'python':sys.version,'platform':platform.platform(),'psycopg':psycopg.__version__},
        'preflight':inventory(),'inputsBefore':inputs(),'status':'RUNNING',
        'limits':['Synthetic per-run revoke and cleanup acknowledgements, no authenticated trust or container cleanup',
            'No capacity/fairness/backup-restore/external blob or ordinary export','No production DB/control/worker decision',
            'S2/P3-B/P4-A/P4-B remain partial']}
    begin=time.monotonic()
    try:
        require(evidence['preflight']['toolchainReady'],'Prerequisites NOT READY')
        experiment(evidence)
        evidence['inputsAfter']=inputs()
        require(evidence['inputsBefore']==evidence['inputsAfter'],'Source/input changed during run')
        evidence['status']='PASS'
    except Exception as error:
        evidence['status']='ERROR'; evidence['errorType']=type(error).__name__
        (CACHE/'s2b-last-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    evidence['finishedAt']=datetime.now(timezone.utc).isoformat()
    evidence['elapsedSeconds']=time.monotonic()-begin
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':evidence['status'],'elapsedSeconds':evidence['elapsedSeconds'],
        'checks':{key:value['status'] for key,value in evidence.get('checks',{}).items()}}))
    return 0 if evidence['status']=='PASS' else 2


if __name__=='__main__':
    mp.freeze_support()
    raise SystemExit(main())
