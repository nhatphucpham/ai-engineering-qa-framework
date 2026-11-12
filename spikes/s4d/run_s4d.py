"""S4-D synthetic active lifecycle against real S4-C owned helper."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
for part in ('spikes/s4c','spikes/iapb'):
    sys.path.insert(0,str(ROOT / part))
from run_s4c import Helper
from run_iapb import AuthorityFixture, require, blocked, wait_due, inventory, db_inventory
from gate import WorkerBridge, VERSION as C_VERSION
from lifecycle import Lifecycle, VERSION
from authority import _AuthorityStore, Denied
import base64, contextlib, hashlib, io, json, multiprocessing as mp, subprocess, time, traceback
from datetime import datetime, timezone

CACHE = ROOT / '.cache/s6/s4-c'

def child(schema, route, body, first, entered, release, started, pipe):
    life = Lifecycle(schema, None)
    try:
        started.set()
        try:
            if first:
                with life.identity.tx():
                    result = getattr(life, route)(**body)
                    entered.set(); require(release.wait(12), 'Ordered release timeout')
            else:
                result = getattr(life, route)(**body)
            pipe.send({'status':'accepted','request':result})
        except Denied as error:
            pipe.send({'status':'denied','code':error.code})
    finally:
        life.close(); pipe.close()


def ordered(schema, first, second):
    entered, release = mp.Event(), mp.Event()
    children=[]; pipes=[]
    try:
        for i,(route,body) in enumerate((first,second)):
            started=mp.Event(); parent,endpoint=mp.Pipe()
            proc=mp.Process(target=child,args=(schema,route,body,i==0,entered,release,started,endpoint))
            proc.start(); endpoint.close(); children.append(proc); pipes.append(parent)
            require(started.wait(12),'Child start timeout')
            if i==0: require(entered.wait(12),'First transaction not held')
        observer=_AuthorityStore(schema)
        try:
            deadline=time.monotonic()+8; locked=False
            while time.monotonic()<deadline:
                locked=observer.conn.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND application_name='s2-synthetic-spike' AND wait_event_type='Lock') AS held").fetchone()['held']
                if locked: break
                time.sleep(.01)
            require(locked,'Contender lock wait not observed')
        finally: observer.close()
        release.set(); outcomes=[]
        for pipe in pipes:
            require(pipe.poll(15),'Child result timeout'); outcomes.append(pipe.recv())
        for proc in children:
            proc.join(10); require(proc.exitcode==0,'Child failed')
        require(outcomes[0]['status']=='accepted' and outcomes[1]['status']=='denied','Not one winner')
        return outcomes
    finally:
        release.set()
        for proc in children:
            if proc.is_alive(): proc.kill(); proc.join(10)
        for pipe in pipes: pipe.close()


def experiment(evidence, forbidden):
    f = AuthorityFixture(forbidden); helper = bridge = life = observer = None
    outstanding = {}
    evidence['schema'] = f.schema; checks = evidence['checks'] = {}
    try:
        f.enroll('schedA','scheduler'); f.enroll('workerA','worker')
        helper = Helper(); evidence['helper'] = helper.ready
        bridge = WorkerBridge(f.schema,helper); life = Lifecycle(f.schema,bridge,create=True); observer = _AuthorityStore(f.schema)
        def status(job):
            return observer.conn.execute('SELECT * FROM d_lifecycle WHERE job_id=%s',(job,)).fetchone()
        def start(name):
            grant = f.new_run(name); assignment = f.assign(name)
            job = bridge.dispatch('prepare',version=C_VERSION,credential=f.tokens['workerA'],**f.binding(assignment))['jobId']
            bridge.dispatch('release',version=C_VERSION,credential=f.tokens['workerA'],job_id=job)
            outstanding[job] = None; life.enroll(job)
            return grant,assignment,job
        def cancel(grant,job):
            return life.cancel(f.users['runner']['access'],grant,job)
        def complete(job):
            return life.complete(f.tokens['workerA'],job)
        def clean(job,request):
            observation = life.cleanup(job,request); del outstanding[job]; return observation
        grant,a,job = start('dCancel')
        blocked(lambda: f.call('cancel',project='pA',grant=grant,key='oldCancel',run_id='dCancel',expected_version=1))
        f.svc('renew','workerA',**f.binding(a),ttl_ms=20000)
        cb={'access':f.users['runner']['access'],'grant':grant,'job':job}
        wb={'credential':f.tokens['workerA'],'job':job}
        race_cancel = ordered(f.schema,('cancel',cb),('complete',wb)); request=race_cancel[0]['request']; outstanding[job]=request
        require(status(job)['state']=='cancelling' and helper.request('registered',job=job)['containerRunningObserved'], 'No active pending cleanup')
        blocked(lambda: life.acknowledge(job,'0'*32,helper.generation),'E_STALE')
        blocked(lambda: life.acknowledge(job,request,'0'*32),'E_STALE')
        require(status(job)['state']=='cancelling' and helper.request('registered',job=job)['containerRunningObserved'], 'Forged ack mutated')
        blocked(lambda: complete(job),'E_STALE')
        blocked(lambda: f.check(a),'E_STALE')
        blocked(lambda: f.svc('renew','workerA',**f.binding(a),ttl_ms=20000),'E_STALE')
        observation = clean(job,request)
        require(status(job)['state']=='cancelled' and status(job)['acked'], 'Cancel not finalized')
        blocked(lambda: life.acknowledge(job,request,helper.generation),'E_STALE')
        checks['D01']={'status':'PASS','pendingWhileContainerRunning':True,'legacyCancelDenied':True,'actualCleanup':observation,'terminal':'cancelled'}
        checks['D04']={'status':'PASS','wrongRequestGenerationAndReplayDenied':True,'originalContainerStillRunningBeforeRealCleanup':True}
        grant,a,job = start('dTimeout'); request = cancel(grant,job); outstanding[job] = request
        original = helper.request
        def outage(*args,**kwargs): raise RuntimeError('synthetic helper outage')
        helper.request=outage
        try:
            try: life.cleanup(job,request)
            except RuntimeError: pass
            else: raise AssertionError('Outage was accepted')
        finally: helper.request=original
        wait_due(observer.conn,"SELECT deadline<=clock_timestamp() AS due FROM d_lifecycle WHERE job_id=%s",(job,))
        life.timeout(job,request)
        require(status(job)['incident_open'] and status(job)['state']=='failed_cleanup_unconfirmed', 'No incident')
        newer=f.assign('dTimeout',expected=1)
        blocked(lambda: bridge.dispatch('prepare',version=C_VERSION,credential=f.tokens['workerA'],**f.binding(newer)))
        observation=clean(job,request)
        require(status(job)['state']=='failed_cleanup_unconfirmed' and not status(job)['incident_open'] and status(job)['acked'], 'Late ack rewrote history')
        blocked(lambda: bridge.dispatch('prepare',version=C_VERSION,credential=f.tokens['workerA'],**f.binding(newer)))
        checks['D02']={'status':'PASS','timeoutIncidentOpenAndNewExecutionBlocked':True,'lateCleanup':observation,'lateState':'failed_cleanup_unconfirmed','automaticRetry':False}
        grant,a,job=start('dComplete')
        cb={'access':f.users['runner']['access'],'grant':grant,'job':job}
        wb={'credential':f.tokens['workerA'],'job':job}
        race_complete=ordered(f.schema,('complete',wb),('cancel',cb)); request=race_complete[0]['request']; outstanding[job]=request
        blocked(lambda: cancel(grant,job),'E_STALE')
        blocked(lambda: f.check(a),'E_STALE')
        blocked(lambda: f.svc('renew','workerA',**f.binding(a),ttl_ms=20000),'E_STALE')
        require(status(job)['state']=='completing' and helper.request('registered',job=job)['containerRunningObserved'],'Completion prematurely terminal')
        observation=clean(job,request)
        require(status(job)['state']=='completed','Completion failed')
        require(observer.conn.execute("SELECT count(*) AS n FROM b_audit WHERE run_id IN ('dCancel','dComplete') AND operation='request_cleanup'").fetchone()['n']==2,'Unexpected cleanup request audit count')
        checks['D03']={'status':'PASS','twoProcessesBothOrderingsWithObservedDBLockWait':True,'cancelFirstAndCompleteFirstOneWinner':True,'completionPendingUntilActualCleanup':True,'actualCleanup':observation}
        metadata=json.dumps({t:observer.conn.execute('SELECT * FROM '+t).fetchall() for t in ('d_lifecycle','launch_jobs','b_audit','app_runs','app_delegations')},default=str).encode()
        require(not any(x in metadata or base64.b64encode(x) in metadata or x.hex().encode() in metadata for x in forbidden),'Credential in metadata')
        evidence['credentialMetadataScan']='PASS'
    finally:
        if bridge:
            for job,request in list(outstanding.items()):
                try:
                    if request is None: bridge._cleanup(job)
                    else: life.cleanup(job,request)
                except Exception: pass
        if observer: observer.close()
        if life: life.close()
        if bridge: bridge.close()
        if helper: evidence['postRunHelper']=helper.close()
        f.close()

def inputs():
    paths=[]
    for folder in ('spikes/s4d','spikes/s4c','spikes/s4b','spikes/s4','spikes/iapb','spikes/iap','spikes/s6b','spikes/s2'):
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT/'docs/S4-D-PROTOCOL.md']
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def main():
    if len(sys.argv)!=2: raise SystemExit('Use fresh docs/s4d-results/<id>.json')
    dest=(ROOT/sys.argv[1]).resolve()
    if dest.parent!=(ROOT/'docs/s4d-results').resolve() or dest.exists() or dest.suffix!='.json': raise SystemExit('Use fresh S4-D evidence path')
    CACHE.mkdir(parents=True,exist_ok=True)
    evidence={'evidenceVersion':VERSION,'classification':'synthetic-only','baseline':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'startedAt':datetime.now(timezone.utc).isoformat(),'inputsBefore':inputs(),'status':'RUNNING','preflight':inventory(),'databasePreflight':db_inventory()}
    forbidden=[]; begin=time.monotonic(); output=io.StringIO(); errors=io.StringIO()
    try:
        require(evidence['preflight']['ready'] and evidence['databasePreflight']['toolchainReady'],'Prerequisites not ready')
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors): experiment(evidence,forbidden)
        captured=(output.getvalue()+errors.getvalue()).encode()
        require(not any(x in captured or base64.b64encode(x) in captured or x.hex().encode() in captured for x in forbidden),'Credential in diagnostics')
        evidence['credentialDiagnosticsScan']='PASS'; evidence['inputsAfter']=inputs()
        require(evidence['inputsBefore']==evidence['inputsAfter'],'Source changed'); evidence['status']='PASS'
    except Exception as error:
        evidence['status']='ERROR'; evidence['errorType']=type(error).__name__
        (CACHE/(dest.stem+'-s4d-error.log')).write_text(traceback.format_exc(),encoding='utf-8')
    evidence['elapsedSeconds']=time.monotonic()-begin; evidence['finishedAt']=datetime.now(timezone.utc).isoformat()
    encoded=json.dumps(evidence,indent=2,default=str).encode()
    require(not any(x in encoded or base64.b64encode(x) in encoded or x.hex().encode() in encoded for x in forbidden),'Credential in evidence')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as stream: stream.write(encoded+b'\n')
    print(json.dumps({'status':evidence['status'],'checks':{k:v['status'] for k,v in evidence.get('checks',{}).items()}}))
    return 0 if evidence['status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
