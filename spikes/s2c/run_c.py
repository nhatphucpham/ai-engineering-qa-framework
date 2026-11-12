"""Actual synthetic PostgreSQL scheduler/metadata restore experiment, not production."""

from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
import traceback
import uuid

from store_c import CapacityStore,Rejected,ROOT,canonical
from backup import fingerprint,create_target,dump,restore,RestoredStore,restore_connection
from local import CACHE,inventory,command,stop,start
from run import require,reject
from run_b import wait_due,observation
from store import psycopg
from qa_core.publication import validate_publication_package


def new_store(caps=(2,1,1),global_cap=3):
    schema='s2_'+uuid.uuid4().hex
    store=CapacityStore(schema,create=True)
    for project,cap in zip(('a','b','c'),caps):store.add_project(project,cap)
    store.configure(global_cap=global_cap)
    return schema,store


def finish(store,claim):
    package=store.package(claim)
    require(package['target']['projectId']==claim['project_id'],'Scheduler/raw project identity mismatch')
    store.accept_receipt(claim,package)
    store.complete(claim,package)
    store.verify_roundtrip(claim,package)


def bulk_process(schema,barrier,pipe):
    results=[]
    def worker():
        store=None
        try:
            store=CapacityStore(schema)
            backend=store.conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
            barrier.wait(timeout=20)
            claims=[];deadline=time.monotonic()+100
            while time.monotonic()<deadline:
                claim=store.claim()
                if claim is not None:
                    finish(store,claim);claims.append(claim['id']);continue
                remaining=store.conn.execute("SELECT count(*) AS n FROM runs WHERE state<>'completed'").fetchone()['n']
                if remaining==0:break
                time.sleep(0.01)
            require(remaining==0 if not claims else
                    store.conn.execute("SELECT count(*) AS n FROM runs WHERE state<>'completed'").fetchone()['n']==0,
                    'Bulk workload timeout')
            results.append({'backend':backend,'process':mp.current_process().pid,'claims':claims})
        except Exception as error:results.append({'status':'ERROR','errorType':type(error).__name__})
        finally:
            if store:store.close()
    threads=[threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:thread.start()
    for thread in threads:thread.join(120)
    pipe.send(results);pipe.close()


def bulk(schema):
    barrier=mp.Barrier(4);children=[];pipes=[]
    for _ in range(2):
        parent,child=mp.Pipe();proc=mp.Process(target=bulk_process,args=(schema,barrier,child))
        proc.start();child.close();children.append(proc);pipes.append(parent)
    try:
        results=[]
        for pipe in pipes:
            require(pipe.poll(130),'Bulk process timed out');results.extend(pipe.recv())
        for proc in children:proc.join(10);require(proc.exitcode==0,'Bulk process exit failed')
        require(len(results)==4 and all(r.get('status')!='ERROR' for r in results),'Bulk connection error: '+str(results))
        require(len({r['backend'] for r in results})==4 and len({r['process'] for r in results})==2,'Bulk process/connection count')
        require(all(r['claims'] for r in results),'Every independent connection must participate')
        all_claims=[name for r in results for name in r['claims']]
        require(len(all_claims)==len(set(all_claims))==100,'Duplicate or missing accepted claim')
        return results
    finally:
        for proc in children:
            if proc.is_alive():proc.kill();proc.join(10)
        for pipe in pipes:pipe.close()


def completion_child(schema,claim,package,pipe):
    store=CapacityStore(schema)
    with store.conn.transaction():
        store.complete(claim,package)
        pipe.send('completion_uncommitted');pipe.recv()
    store.close()


def deliver(store,event_id,sink,ack=True):
    row=store.conn.execute('SELECT * FROM outbox WHERE id=%s AND NOT acked',(event_id,)).fetchone()
    if row is None:return False
    with sink.open('a',encoding='utf-8') as stream:
        stream.write(event_id+'\n');stream.flush()
        import os
        os.fsync(stream.fileno())
    if ack:store.conn.execute('UPDATE outbox SET acked=true WHERE id=%s',(event_id,))
    return True


def experiment(evidence):
    schemas=evidence['schemas']={}
    checks=evidence['checks']={}
    schema,store=new_store();schemas['bulk_and_restore']=schema
    try:
        evidence['database']=store.conn.execute("SELECT version() AS version,current_setting('fsync') AS fsync,current_setting('synchronous_commit') AS synchronous_commit").fetchone()
        require(evidence['database']['fsync']==evidence['database']['synchronous_commit']=='on','DB durability settings')
        for project,count in (('a',90),('b',5),('c',5)):
            for index in range(count):store.seed(f'{project}-{index:03}',project)
        workers=bulk(schema)
        logs=store.conn.execute('SELECT * FROM admissions ORDER BY turn').fetchall()
        for row in logs:
            require(sum(row['occupancy'].values())+1<=row['global_cap'],'Global over-admission')
            require(row['occupancy'].get(row['project_id'],0)+1<=row['project_cap'],'Project over-admission')
        require(store.conn.execute('SELECT count(*) AS n FROM reports').fetchone()['n']==100 and
                store.conn.execute('SELECT count(*) AS n FROM outbox').fetchone()['n']==100,'Bulk atomic graph count')
        checks['C01']={'status':'PASS','workers':workers,'admissions':logs,'max_total_after_admission':max(sum(r['occupancy'].values())+1 for r in logs)}
        skips={p:0 for p in ('a','b','c')};max_skips=dict(skips)
        for row in logs:
            eligible=row['eligible']
            require(row['project_id']==min(eligible,key=lambda p:(p['last_served'],p['project_id']))['project_id'],'Fair project order')
            ids={p['project_id'] for p in eligible}
            for project in skips:
                skips[project]=skips[project]+1 if project in ids and project!=row['project_id'] else 0
                max_skips[project]=max(max_skips[project],skips[project])
                require(skips[project]<=2,'Continuously eligible project skipped more than N-1')
        age=sorted(float(row['queue_age_ms']) for row in logs)
        fair_schema,fair=new_store();schemas['ordered_fairness']=fair_schema
        try:
            for project in ('a','b','c'):
                for index in range(3):fair.seed(f'fair-{project}-{index}',project)
            require(fair.claim('fair-a-1') is None,'Targeted claim skipped FIFO head')
            order=[]
            for _ in range(9):
                claim=fair.claim();order.append(claim['project_id']);finish(fair,claim)
            require(order==['a','b','c']*3,'Deterministic fairness round mismatch')
        finally:fair.close()
        checks['C04']={'status':'PASS','ordered_sequence':order,'targeted_tail_refused':True,'max_continuously_eligible_skips':max_skips,
                      'queue_age_ms':{'median':statistics.median(age),'p95_nearest_rank':age[94],'max':max(age)}}

        cap_schema,cap=new_store(caps=(2,1,1));schemas['capacity_and_lock']=cap_schema
        try:
            for project in ('a','b','c'):
                for index in range(4):cap.seed(f'cap-{project}-{index}',project)
            a1=cap.claim('cap-a-0');a2=cap.claim('cap-a-1');b1=cap.claim('cap-b-0')
            require(cap.claim('cap-c-0') is None,'Global cap bypassed')
            before=fingerprint(cap,cap_schema)
            for value in (True,1.5,0,-1):
                reject(lambda:cap.configure(global_cap=value));reject(lambda:cap.configure(project_id='a',project_cap=value))
            reject(lambda:cap.configure(global_cap=2));reject(lambda:cap.configure(project_id='a',project_cap=1))
            require(fingerprint(cap,cap_schema)==before,'Invalid config changed state')
            finish(cap,a1);c1=cap.claim('cap-c-0');require(c1 is not None,'Other project could not use freed capacity')
            cap.configure(project_id='a',project_cap=1);finish(cap,b1)
            require(cap.claim('cap-a-2') is None,'Per-project cap bypassed')
            b2=cap.claim('cap-b-1');require(b2 is not None,'Full project blocked another project')
            for claim in (a2,c1,b2):finish(cap,claim)
            # A separate connection holds all queued rows of least-served project a.
            cap.configure(project_id='a',project_cap=2)
            cap.conn.execute('UPDATE projects SET last_served=CASE WHEN project_id=\'a\' THEN 0 ELSE 1000 END')
            locker=CapacityStore(cap_schema)
            try:
                with locker.conn.transaction():
                    locker.conn.execute("SELECT * FROM runs WHERE project_id='a' AND state='queued' FOR UPDATE")
                    unblocked=cap.claim()
                    require(unblocked is not None and unblocked['project_id']!='a','Locked queue blocked other projects')
                finish(cap,unblocked)
            finally:locker.close()
            cap.conn.execute('UPDATE projects SET last_served=CASE WHEN project_id=\'a\' THEN 0 ELSE 1000 END')
            locker=CapacityStore(cap_schema)
            try:
                with locker.conn.transaction():
                    head=locker.conn.execute("SELECT id FROM runs WHERE project_id='a' AND state='queued' ORDER BY queued_at,id LIMIT 1 FOR UPDATE").fetchone()['id']
                    queued_a=cap.conn.execute("SELECT id FROM runs WHERE project_id='a' AND state='queued' ORDER BY queued_at,id").fetchall()
                    require(len(queued_a)>=2,'FIFO locked-head probe needs an unlocked later job')
                    head_bypass=cap.claim()
                    require(head_bypass is not None and head_bypass['project_id']!='a','Locked FIFO head was skipped within project')
                    require(all(cap.row(item['id'])['state']=='queued' for item in queued_a),'FIFO tail admitted before locked head')
                finish(cap,head_bypass)
            finally:locker.close()
            checks['C02']={'status':'PASS','occupancy':cap.occupancy(),'locked_project':'a','other_project_claim':unblocked,
                           'locked_fifo_head':head,'head_blocked_other_project_claim':head_bypass,'fifo_tail_untouched':True,
                           'invalid_config_unchanged':True,'global_cap':3,'project_caps':{'a':2,'b':1,'c':1}}
        finally:cap.close()

        cleanup_schema,clean=new_store(caps=(1,1,1),global_cap=1);schemas['cleanup_occupancy']=cleanup_schema
        try:
            clean.seed('orphan','a');clean.seed('next-b','b');clean.seed('cancel-a','a');clean.seed('last-b','b')
            old=clean.claim('orphan',ttl_ms=250);wait_due(clean,old['id'])
            expired_counts=clean.occupancy();require(expired_counts=={'a':1} and clean.claim('next-b') is None,'Expired lease freed slot')
            request=clean.reconcile_expired(old['id'],cleanup_ms=100)
            ack=observation(clean,old['id'],request)
            recovering_counts=clean.occupancy();require(recovering_counts=={'a':1},'Recovery freed slot')
            wait_due(clean,old['id'],'cleanup_deadline');clean.cleanup_timeout(old['id'])
            failed=clean.snapshot(old['id']);require(clean.occupancy()=={'a':1} and clean.claim('next-b') is None,'Failed cleanup leaked slot')
            clean.close();store.close();stop();start()
            clean=CapacityStore(cleanup_schema);store=CapacityStore(schema)
            require(clean.occupancy()=={'a':1} and clean.claim('next-b') is None,'Restart lost pending occupancy')
            clean.ack_cleanup(**ack)
            require(clean.occupancy()=={} and clean.snapshot(old['id'])['state']=='failed','Late ack did not release only slot')
            current=clean.claim('next-b');require(current is not None,'Cleanup ack failed to free slot');finish(clean,current)
            current=clean.claim('cancel-a');request=clean.request_stop(current['id'],current['version'])
            cancelling=clean.snapshot(current['id']);require(clean.occupancy()=={'a':1} and clean.claim('last-b') is None,'Cancelling freed slot early')
            clean.ack_cleanup(**observation(clean,current['id'],request));current=clean.claim('last-b');finish(clean,current)
            checks['C03']={'status':'PASS','expired_occupancy':expired_counts,'recovering_occupancy':recovering_counts,
                           'failed_pending':failed,'cancelling_pending':cancelling,'after_cleanup':clean.occupancy(),'restart_preserved_slot':True}
        finally:clean.close()

        rollback_schema,rolled=new_store();schemas['rollback']=rollback_schema
        try:
            rolled.seed('rollback-a','a');before=fingerprint(rolled,rollback_schema);observer=CapacityStore(rollback_schema)
            observed=[]
            class Fault(Exception):pass
            def fault():observed.append(fingerprint(observer,rollback_schema));raise Fault()
            try:rolled.claim(before_commit=fault)
            except Fault:pass
            observer.close()
            require(observed==[before] and fingerprint(rolled,rollback_schema)==before,'Rollback exposed partial claim/turn/attempt')
            retry=rolled.claim();require(retry['turn']==1 and retry['attempt']==1,'Rolled-back admission consumed turn/attempt')
            checks['C05']={'status':'PASS','before_and_observer':before,'after_rollback_unchanged':True,'retry':retry}
        finally:rolled.close()

        # Dump committed metadata while a separate process has all completion graph writes uncommitted.
        acked_id='ready-a-000';pending_id='ready-b-000'
        store.conn.execute('UPDATE outbox SET acked=true WHERE id=%s',(acked_id,))
        store.seed('backup-open','a');open_claim=store.claim('backup-open');package=store.package(open_claim)
        store.accept_receipt(open_claim,package)
        before=fingerprint(store,schema)
        report_rows=store.conn.execute('''SELECT p.*,r.bundle_sha,r.assessment_sha FROM reports p JOIN runs r ON r.id=p.run_id''').fetchall()
        parent,child=mp.Pipe();proc=mp.Process(target=completion_child,args=(schema,open_claim,package,child))
        proc.start();child.close()
        archive=CACHE/('s2c-'+schema+'.dump')
        try:
            require(parent.poll(20) and parent.recv()=='completion_uncommitted','Backup child fault point missing')
            archive_sha=dump(schema,archive)
            require(fingerprint(store,schema)==before,'Uncommitted completion visible during dump')
            proc.terminate();proc.join(10);require(not proc.is_alive() and proc.exitcode!=0,'Dump child kill failed')
        finally:
            if proc.is_alive():proc.kill();proc.join(10)
            parent.close()
        require(fingerprint(store,schema)==before,'Source changed after child rollback')
        checks['R01']={'status':'PASS','source_fingerprint':before,'archive_sha256':archive_sha,'archive_bytes':archive.stat().st_size,
                       'child_exitcode':proc.exitcode,'uncommitted_graph_excluded':True}
        database=create_target();evidence['restoreDatabase']=database
        truncated=CACHE/('truncated-'+schema+'.dump');truncated.write_bytes(archive.read_bytes()[:archive.stat().st_size//2])
        try:restore(database,schema,truncated,hashlib.sha256(truncated.read_bytes()).hexdigest())
        except subprocess.CalledProcessError as error:failed_code=error.returncode
        else:raise AssertionError('Truncated restore unexpectedly succeeded')
        target=restore_connection(database)
        require(target.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(schema,)).fetchone() is None,'Partial restore schema remained')
        target.close()
        checks['R02']={'status':'PASS','truncated_restore_exitcode':failed_code,'partial_namespace_present':False}
        # Hash mismatch rejected before tool execution; authentic archive retained.
        try:restore(database,schema,archive,'0'*64)
        except ValueError:pass
        else:raise AssertionError('Wrong archive anchor accepted')
        restore(database,schema,archive,archive_sha)
        restored=RestoredStore(database,schema)
        try:
            after=fingerprint(restored,schema);require(after==before,'Restored tables differ from committed source snapshot')
            checked=[]
            for source in report_rows:
                target=restored.conn.execute('SELECT * FROM reports WHERE id=%s',(source['id'],)).fetchone()
                require(bytes(target['package'])==bytes(source['package']),'Canonical package bytea changed')
                payload=json.loads(bytes(target['package']))
                require(not validate_publication_package(payload,expected_bundle_sha256=source['bundle_sha'],
                    expected_assessment_sha256=source['assessment_sha'],run_id=source['run_id'],report_id=source['id']),
                    'Restored package failed independent source anchors')
                checked.append({'id':source['id'],'sha256':source['package_sha'],'length':source['package_length']})
            require(restored.snapshot('backup-open')['state']=='checking' and restored.snapshot('backup-open')['reports']==0,'Uncommitted report was restored')
            try:restore(database,schema,archive,archive_sha)
            except ValueError:pass
            else:raise AssertionError('Existing namespace overwrite accepted')
            checks['R03']={'status':'PASS','restored_fingerprint':after,'exact_packages_checked':checked,'source_anchors_used':True,
                           'existing_target_refused':True,'wrong_archive_anchor_refused':True}
            sink=CACHE/('restore-sink-'+schema+'.txt')
            require(not deliver(restored,acked_id,sink),'Previously acked event sent after restore')
            require(deliver(restored,pending_id,sink,ack=False) and deliver(restored,pending_id,sink,ack=True),'Pending replay missing')
            require(not deliver(restored,pending_id,sink) and sink.read_text().splitlines()==[pending_id,pending_id],'Replay stable identity/ack mismatch')
            require(fingerprint(store,schema)==before,'Restore/replay changed source database')
            checks['R04']={'status':'PASS','sink':[pending_id,pending_id],'acked_event_skipped':acked_id,
                           'source_unchanged':True,'restore_auto_sent_events':0}
        finally:restored.close()
    finally:store.close()


def inputs():
    paths=set()
    for name in ('qa_core','schemas','spikes/s2','spikes/s2b','spikes/s2c','examples/reports/runtime-v1'):
        paths.update(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.add(ROOT/'docs/S2-C-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: py -3 -B spikes/s2c/run_c.py docs/s2c-results/<new-id>.json')
    destination=(ROOT/sys.argv[1]).resolve()
    if destination.parent!=(ROOT/'docs/s2c-results').resolve() or destination.exists() or destination.suffix!='.json':
        raise SystemExit('Use a new JSON evidence path under docs/s2c-results')
    evidence={'evidenceVersion':'s2-c-1.0.0','classification':'synthetic-only',
        'baseline':subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),
        'startedAt':datetime.now(timezone.utc).isoformat(),'command':'py -3 -B spikes/s2c/run_c.py '+sys.argv[1],
        'environment':{'python':sys.version,'platform':platform.platform(),'psycopg':psycopg.__version__},
        'preflight':inventory(),'inputsBefore':inputs(),'status':'RUNNING',
        'limits':['Metadata admission/cleanup predicates, no physical worker/container/auth controls',
            'Fixture round-robin eligibility, no production SLA/fairness guarantee','DB schema-only restore; no external blob/key/roles/cluster/PITR recovery',
            'No production DB/control/worker choice; full S2/P3-B/P4-A/P4-B remain partial']}
    begin=time.monotonic()
    try:
        require(evidence['preflight']['toolchainReady'],'Prerequisites NOT READY')
        evidence['pg_dump']=command('pg_dump','--version');evidence['pg_restore']=command('pg_restore','--version')
        experiment(evidence);evidence['inputsAfter']=inputs()
        require(evidence['inputsBefore']==evidence['inputsAfter'],'Source/input changed during run')
        evidence['status']='PASS'
    except Exception as error:
        evidence['status']='ERROR';evidence['errorType']=type(error).__name__
        (CACHE/'s2c-last-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    evidence['elapsedSeconds']=time.monotonic()-begin;evidence['finishedAt']=datetime.now(timezone.utc).isoformat()
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(evidence,indent=2,default=lambda value:str(value) if isinstance(value,Decimal) else value)+'\n',encoding='utf-8')
    print(json.dumps({'status':evidence['status'],'elapsedSeconds':evidence['elapsedSeconds'],
                     'checks':{key:value['status'] for key,value in evidence.get('checks',{}).items()}}))
    return 0 if evidence['status']=='PASS' else 2


if __name__=='__main__':
    mp.freeze_support();raise SystemExit(main())
