"""Actual Argon2/DB identity fixture. Tokens/passwords stay out of emitted evidence."""
from preflight_b import ROOT,CACHE,inventory
import json,sys
prereq=inventory()
if not prereq['ready']:
    print(json.dumps({'status':'NOT READY','details':prereq,'execution':'NOT RUN'}));raise SystemExit(2)
import base64,contextlib,hashlib,io,multiprocessing as mp,secrets,statistics,subprocess,time,traceback,uuid
from datetime import datetime,timezone
from identity import Identity,_Store,Denied,PH,READ,digest
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from local import inventory as db_inventory,stop,start

def require(condition,message):
    if not condition:raise AssertionError(message)
def deny(action):
    try:action()
    except Denied as error:return error.code
    raise AssertionError('Expected denial')
def pw(forbidden):
    value='synthetic-'+secrets.token_urlsafe(24);forbidden.append(value.encode());return value
def keep(pair,forbidden):
    forbidden.extend(value.encode() for value in pair.values());return pair
def wait_budget(store,user):
    limit=time.monotonic()+3
    while time.monotonic()<limit:
        row=store.conn.execute("SELECT attempts<3 OR window_start<clock_timestamp()-interval '1 second' AS ok FROM login_buckets WHERE bucket=%s",(hashlib.sha256(user.encode()).hexdigest(),)).fetchone()
        if row is None or row['ok']:return
        time.sleep(.01)
    raise AssertionError('Login budget did not reset')
def login(api,store,user,password,forbidden):
    wait_budget(store,user);return keep(api.dispatch('login',user=user,pw=password),forbidden)
def activate(api,store,user,password,forbidden):
    restricted=login(api,store,user,password,forbidden)
    replacement=pw(forbidden);api.dispatch('password_change',access=restricted['access'],old=password,new=replacement)
    deny(lambda:api.dispatch('grant',access=restricted['access'],project='pA',actions=['read']))
    deny(lambda:api.dispatch('refresh',token=restricted['refresh']))
    return login(api,store,user,replacement,forbidden),replacement
def wait_token(store,token,kind='a'):
    table='access_tokens' if kind=='a' else 'refresh_tokens';deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        if store.conn.execute(f'SELECT expires<=clock_timestamp() AS due FROM {table} WHERE digest=%s',(digest(token,kind),)).fetchone()['due']:return
        time.sleep(.01)
    raise AssertionError('DB expiry did not arrive')

def concurrent_child(schema,operation,body,barrier,pipe):
    api=Identity(schema)
    try:
        barrier.wait(timeout=20)
        try:result=api.dispatch(operation,**body);pipe.send({'status':'accepted','result':result})
        except Denied as error:pipe.send({'status':'denied','code':error.code})
    finally:api.close();pipe.close()
def race(schema,requests):
    gate=mp.Barrier(2);children=[];pipes=[]
    for operation,body in requests:
        parent,child=mp.Pipe();proc=mp.Process(target=concurrent_child,args=(schema,operation,body,gate,child));proc.start();child.close();children.append(proc);pipes.append(parent)
    try:
        results=[]
        for pipe in pipes:require(pipe.poll(25),'Identity race timeout');results.append(pipe.recv())
        for proc in children:proc.join(10);require(proc.exitcode==0,'Identity race failed')
        return results
    finally:
        for proc in children:
            if proc.is_alive():proc.kill();proc.join(10)
        for pipe in pipes:pipe.close()

def experiment(evidence,forbidden):
    schema='id_'+uuid.uuid4().hex;evidence['schema']=schema;store=_Store(schema,create=True);api=Identity(schema)
    checks=evidence['checks']={}
    try:
        sample='  Σynthetic_'+secrets.token_hex(16)+'  ';forbidden.append(sample.encode());durations=[];hashes=[]
        for _ in range(5):
            begin=time.perf_counter();encoded=PH.hash(sample);durations.append((time.perf_counter()-begin)*1000);hashes.append(encoded)
            require(PH.verify(encoded,sample) and not PH.check_needs_rehash(encoded),'Hash verify/parameters mismatch')
        try:PH.verify(hashes[0],sample.strip())
        except VerificationError:pass
        else:raise AssertionError('Password silently trimmed')
        require(len(set(hashes))==5 and all(h.startswith('$argon2id$') for h in hashes),'Salt/type mismatch');forbidden.extend(h.encode() for h in hashes)
        legacy=PasswordHasher(time_cost=1,memory_cost=8192,parallelism=1).hash(sample)
        forbidden.append(legacy.encode())
        require(PH.verify(legacy,sample) and PH.check_needs_rehash(legacy),'Legacy parameters not recognized for rehash')
        checks['I01']={'status':'PASS','profile':{'type':'Argon2id','memory_KiB':PH.memory_cost,'time_cost':PH.time_cost,'parallelism':PH.parallelism,'hash_len':PH.hash_len,'salt_len':PH.salt_len},
            'hash_ms_samples':durations,'median_ms':statistics.median(durations),'p95_nearest_rank_ms':max(durations),'distinct_salts':5,'no_trim':True,
            'legacy_parameter_hash_verifies_and_needs_rehash':True}
        initial=pw(forbidden);store.bootstrap('root',initial)
        deny(lambda:store.bootstrap('again',pw(forbidden)))
        restricted=login(api,store,'root',initial,forbidden)
        deny(lambda:api.dispatch('account_create',access=restricted['access'],user='illegal',pw=pw(forbidden)))
        admin,admin_pw=activate(api,store,'root',initial,forbidden)
        for op in ('issue','_issue','bootstrap','principal','tx','conn','__dict__'):
            deny(lambda:api.dispatch(op,user='root'))
        require(not hasattr(api,'issue') and not hasattr(api,'conn'),'Facade exposes authority helper')
        deny(lambda:api.dispatch('login',user='root',pw=admin_pw,access_ms=1800000))
        users={};passwords={}
        for user in ('owner','runner','viewer','other','second','disabled'):
            initial=pw(forbidden);api.dispatch('account_create',access=admin['access'],user=user,pw=initial)
            users[user],passwords[user]=activate(api,store,user,initial,forbidden)
        api.dispatch('project_create',access=admin['access'],project='pA',owner='owner')
        api.dispatch('project_create',access=admin['access'],project='pB',owner='other')
        for user,role in (('runner','Runner'),('viewer','Viewer'),('second','Runner')):
            api.dispatch('membership',access=admin['access'],project='pA',target=user,role=role)
        api.dispatch('account_flag',access=admin['access'],user='disabled',field='enabled',value=False)
        disabled=users['disabled']
        deny(lambda:api.dispatch('grant',access=disabled['access'],project='pA',actions=['read']))
        deny(lambda:api.dispatch('refresh',token=disabled['refresh']))
        errors=[]
        for user,password in (('unknown',pw(forbidden)),('runner',pw(forbidden)),('disabled',passwords['disabled'])):
            wait_budget(store,user);errors.append(deny(lambda:api.dispatch('login',user=user,pw=password)))
        require(errors==['E_AUTH']*3,'Credential error reveals category')
        for _ in range(4):deny(lambda:api.dispatch('login',user='throttle',pw=pw(forbidden)))
        attempts=store.conn.execute('SELECT attempts FROM login_buckets WHERE bucket=%s',(hashlib.sha256(b'throttle').hexdigest(),)).fetchone()['attempts']
        require(attempts==3,'Denied login transaction lost durable throttle counters')
        checks['I02']={'status':'PASS','bootstrap_once':True,'restricted_before_password_change':True,'facade_helper_impersonation_refused':True,
                       'server_ttl_override_refused':True,'generic_errors':errors,'throttle_admitted_attempts':attempts}
        runner=users['runner'];grant=api.dispatch('grant',access=runner['access'],project='pA',actions=['read','start','cancel'])
        fresh=keep(api.dispatch('refresh',token=runner['refresh']),forbidden)
        deny(lambda:api.dispatch('check',access=runner['access'],project='pA',action='read',grant=grant))
        require(api.dispatch('check',access=fresh['access'],project='pA',action='read',grant=grant)['user']=='runner','Refreshed access invalid')
        deny(lambda:api.dispatch('refresh',token=fresh['access']))
        api.dispatch('logout',access=fresh['access']);deny(lambda:api.dispatch('refresh',token=fresh['refresh']))
        wait_budget(store,'runner');short=keep(store.login('runner',passwords['runner'],access_ms=250),forbidden)
        wait_token(store,short['access']);deny(lambda:api.dispatch('check',access=short['access'],project='pA',action='read',grant=grant))
        wait_budget(store,'runner');short_r=keep(store.login('runner',passwords['runner'],refresh_ms=250),forbidden)
        wait_token(store,short_r['refresh'],'r');deny(lambda:api.dispatch('refresh',token=short_r['refresh']))
        checks['I03']={'status':'PASS','old_access_invalid':True,'token_kinds_separate':True,'logout_revokes_family':True,'db_clock_expiry':True}
        current=login(api,store,'runner',passwords['runner'],forbidden)
        outcomes=race(schema,[('refresh',{'token':current['refresh']})]*2)
        require(sum(row['status']=='accepted' for row in outcomes)==1,'Refresh race did not serialize one consumption')
        winner=keep(next(row['result'] for row in outcomes if row['status']=='accepted'),forbidden)
        for pair in (current,winner):deny(lambda:api.dispatch('check',access=pair['access'],project='pA',action='read',grant=grant))
        deny(lambda:api.dispatch('refresh',token=winner['refresh']))
        checks['I04']={'status':'PASS','two_process_outcomes':[{'status':row['status'],'code':row.get('code')} for row in outcomes],
                       'reuse_revoked_new_generation':True,'concurrent_refresh_requires_reauthentication':True}
        old=login(api,store,'runner',passwords['runner'],forbidden);reset=pw(forbidden)
        api.dispatch('account_reset',access=admin['access'],user='runner',new=reset)
        deny(lambda:api.dispatch('refresh',token=old['refresh']));deny(lambda:api.dispatch('check',access=old['access'],project='pA',action='read',grant=grant))
        users['runner'],passwords['runner']=activate(api,store,'runner',reset,forbidden)
        api.close();store.close();stop();start();store=_Store(schema);api=Identity(schema)
        deny(lambda:api.dispatch('refresh',token=old['refresh']))
        deny(lambda:api.dispatch('grant',access=old['access'],project='pA',actions=['read']))
        deny(lambda:api.dispatch('grant',access=disabled['access'],project='pA',actions=['read']))
        deny(lambda:api.dispatch('refresh',token=disabled['refresh']))
        checks['I05']={'status':'PASS','reset_invalidates_access_and_refresh':True,'reset_requires_password_change':True,
                       'change_invalidates_old_access_and_refresh':True,'disable_invalidates_old_access_and_refresh':True,
                       'reset_and_disable_access_and_refresh_denied_after_restart':True,'restart_did_not_revive':True}
        owner=users['owner'];viewer=users['viewer'];second=users['second'];other=users['other']
        for role in ('Owner','Admin'):
            deny(lambda:api.dispatch('membership',access=owner['access'],project='pA',target='viewer',role=role))
        for role in ('Viewer',None):
            deny(lambda:api.dispatch('membership',access=owner['access'],project='pA',target='owner',role=role))
        require(store.conn.execute("SELECT user_id FROM members WHERE project='pA' AND role='Owner'").fetchone()=={'user_id':'owner'},'Denied Owner demotion/removal changed current Owner')
        deny(lambda:api.dispatch('account_flag',access=owner['access'],user='owner',field='admin',value=True))
        deny(lambda:api.dispatch('membership',access=owner['access'],project='pB',target='viewer',role='Runner'))
        deny(lambda:api.dispatch('grant',access=viewer['access'],project='pA',actions=['start']))
        view_grant=api.dispatch('grant',access=viewer['access'],project='pA',actions=['read'])
        deny(lambda:api.dispatch('check',access=viewer['access'],project='pA',action='start',grant=view_grant,role='Admin',authorized=True))
        deny(lambda:api.dispatch('check',access=viewer['access'],project='pB',action='read',grant=view_grant))
        for pair in (admin,owner,viewer,second):
            deny(lambda:api.dispatch('grant',access=pair['access'],project='pA',actions=['reveal_secret']))
            deny(lambda:api.dispatch('grant',access=pair['access'],project='pA',actions=['approve']))
        api.dispatch('membership',access=admin['access'],project='pA',target='viewer',role='Owner')
        require(store.conn.execute("SELECT user_id FROM members WHERE project='pA' AND role='Owner'").fetchone()['user_id']=='viewer','Owner transfer failed')
        # Restore owner fixture for subsequent rights checks.
        api.dispatch('membership',access=admin['access'],project='pA',target='owner',role='Owner')
        api.dispatch('membership',access=admin['access'],project='pA',target='viewer',role='Viewer')
        checks['I06']={'status':'PASS','owner_admin_escalation_denied':True,'owner_transfer_admin_only':True,'cross_project_denied':True,
                       'current_owner_demotion_and_removal_denied_unchanged':True,
                       'viewer_start_denied':True,'client_claims_not_authority':True,'secret_and_approval_actions_denied_all_roles':True}
        live=users['runner'];run_grant=api.dispatch('grant',access=live['access'],project='pA',actions=['read','start','cancel'])
        other_grant=api.dispatch('grant',access=second['access'],project='pA',actions=['start','cancel'])
        api.dispatch('run_start',access=second['access'],project='pA',run_id='foreignRun',grant=other_grant)
        deny(lambda:api.dispatch('run_cancel',access=live['access'],run_id='foreignRun',grant=run_grant))
        api.dispatch('run_start',access=live['access'],project='pA',run_id='ownRun',grant=run_grant)
        api.dispatch('run_cancel',access=live['access'],run_id='ownRun',grant=run_grant)
        owner_grant=api.dispatch('grant',access=owner['access'],project='pA',actions=['cancel'])
        api.dispatch('run_cancel',access=owner['access'],run_id='foreignRun',grant=owner_grant)
        api.dispatch('membership',access=admin['access'],project='pA',target='viewer',role='Runner')
        deny(lambda:api.dispatch('run_start',access=viewer['access'],project='pA',run_id='promotedRun',grant=view_grant))
        api.dispatch('membership',access=admin['access'],project='pA',target='runner',role='Viewer')
        deny(lambda:api.dispatch('run_start',access=live['access'],project='pA',run_id='downgradedRun',grant=run_grant))
        api.dispatch('membership',access=admin['access'],project='pA',target='runner',role='Runner')
        api.dispatch('project_enabled',access=admin['access'],project='pA',enabled=False)
        deny(lambda:api.dispatch('check',access=live['access'],project='pA',action='read',grant=run_grant))
        api.dispatch('project_enabled',access=admin['access'],project='pA',enabled=True)
        api.dispatch('membership',access=admin['access'],project='pA',target='runner',role=None)
        deny(lambda:api.dispatch('check',access=live['access'],project='pA',action='read',grant=run_grant))
        api.dispatch('membership',access=admin['access'],project='pA',target='runner',role='Runner')
        checks['I07']={'status':'PASS','snapshot_promotion_not_expanded':True,'live_downgrade_remove_disable_deny':True,
                       'initiator_server_owned':True,'runner_cancel_own_only':True,'owner_cancel_foreign':True}
        wait_budget(store,'runner');expiring=keep(store.login('runner',passwords['runner'],access_ms=800),forbidden)
        reached=[]
        def delay():reached.append(True);wait_token(store,expiring['access'])
        deny(lambda:store.start_run(expiring['access'],'pA','expiredCommit',run_grant,before_finish=delay))
        require(reached==[True] and store.conn.execute("SELECT 1 FROM qa_runs WHERE id='expiredCommit'").fetchone() is None,'Expiry did not rollback entire proposed run')
        wait_budget(store,'runner');expiring_r=keep(store.login('runner',passwords['runner'],refresh_ms=300),forbidden)
        reached_r=[]
        def delay_r():reached_r.append(True);wait_token(store,expiring_r['refresh'],'r')
        deny(lambda:store.refresh(expiring_r['refresh'],before_write=delay_r));require(reached_r==[True],'Refresh boundary hook not reached')
        checks['I08']={'status':'PASS','access_expired_before_final_conditional_mutation':True,'proposed_run_rolled_back':True,'refresh_crossed_expiry_before_write':True}
        # Last enabled Admin tested with two independent process actors, each trying self-disable.
        api.dispatch('account_flag',access=admin['access'],user='second',field='admin',value=True)
        second_admin=login(api,store,'second',passwords['second'],forbidden)
        outcomes=race(schema,[('account_flag',{'access':admin['access'],'user':'root','field':'enabled','value':False}),
                              ('account_flag',{'access':second_admin['access'],'user':'second','field':'enabled','value':False})])
        require(sum(row['status']=='accepted' for row in outcomes)==1 and store.conn.execute('SELECT count(*) AS n FROM accounts WHERE admin AND enabled').fetchone()['n']==1,'Last-admin concurrent invariant failed')
        checks['I06']['last_admin_race']=[{'status':row['status'],'code':row.get('code')} for row in outcomes]
        # Actual CLI failure paths; no session/encoded password is ever emitted by the facade diagnostic.
        rows=store.conn.execute('SELECT password_hash FROM accounts').fetchall()
        stored_hashes=[row['password_hash'] for row in rows]
        stored_hashes.append(store.conn.execute('SELECT dummy_hash FROM control WHERE id=1').fetchone()['dummy_hash'])
        forbidden.extend(value.encode() for value in stored_hashes)
        captures=[];capture_buffers=[]
        requests=[('unknown_user',{'operation':'login','body':{'user':'cliUnknown','pw':pw(forbidden)}}),
                  ('forged_access',{'operation':'grant','body':{'access':'a.'+secrets.token_urlsafe(32),'project':'pA','actions':['read']}}),
                  ('wrong_token_kind',{'operation':'refresh','body':{'token':live['access']}}),
                  ('helper_impersonation',{'operation':'_issue','body':{'user':'root'}})]
        for label,request in requests:
            path=CACHE/('probe-'+uuid.uuid4().hex+'.json');path.write_text(json.dumps(request),encoding='utf-8')
            out=subprocess.run([sys.executable,'-B',str(ROOT/'spikes/s6b/probe_b.py'),schema,str(path)],capture_output=True,text=True,timeout=20)
            raw=(out.stdout+out.stderr).encode();require(out.returncode==2 and not out.stderr,'CLI failed unsafely')
            capture_buffers.append(raw)
            value=json.loads(out.stdout);require(set(value)=={'status','code'} and value['status']=='blocked' and value['code'] in ('E_AUTH','E_DENIED'),'CLI failure taxonomy')
            require(all(token not in raw and base64.b64encode(token) not in raw and token.hex().encode() not in raw for token in forbidden),'Credential in captured CLI output')
            captures.append({'case':label,'exitcode':out.returncode,'code':value['code'],'stderr_bytes':0})
        require(all(token not in raw and base64.b64encode(token) not in raw and token.hex().encode() not in raw
                    for raw in capture_buffers for token in forbidden),'Credential/hash in retained CLI output')
        forensic=b''
        for table in ('accounts','families','access_tokens','refresh_tokens','audit'):
            records=store.conn.execute('SELECT * FROM '+table).fetchall()
            for row in records:
                for key,value in row.items():
                    if key!='password_hash':forensic+=str(value).encode()
        require(all(token not in forensic for token in forbidden),'Raw credential/encoded password in audit or non-hash fields')
        checks['I09']={'status':'PASS','captured_cli_cases':captures,'passwords_argon2id_only':all(row['password_hash'].startswith('$argon2id$') for row in rows),
                       'raw_credentials_in_db_audit_outputs':False,'hashes_not_in_evidence':True,
                       'cli_scanned_current_account_and_dummy_hashes':True,'cli_encoding_forms':['raw','base64','hex']}
    finally:api.close();store.close()

def inputs():
    paths=set()
    for name in ('qa_core','schemas','spikes/s2','spikes/s6b'):
        paths.update(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.add(ROOT/'docs/S6-B-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: py -3 -B spikes/s6b/run_b.py docs/s6b-results/<new-id>.json')
    dest=(ROOT/sys.argv[1]).resolve()
    if dest.parent!=(ROOT/'docs/s6b-results').resolve() or dest.exists() or dest.suffix!='.json':raise SystemExit('Use a new S6-B evidence path')
    evidence={'evidenceVersion':'s6-b-1.0.0','classification':'synthetic-only','baseline':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'startedAt':datetime.now(timezone.utc).isoformat(),'command':'py -3 -B spikes/s6b/run_b.py '+sys.argv[1],'preflight':prereq,
        'database_preflight':db_inventory(),'inputsBefore':inputs(),'status':'RUNNING','limits':['In-process explicit facade; trusted Python host/DB, no sandbox or HTTP deployment',
            'Fixture TTL/rate/Argon parameters, no production security/performance decision','No OS credentials/TLS/CSRF/SSO/worker/service broker binding','Full S6/P3-B/P4-B open; S4 actual engine gates NOT RUN']}
    begin=time.monotonic();forbidden=[];stdout=io.StringIO();stderr=io.StringIO()
    try:
        require(evidence['database_preflight']['toolchainReady'],'DB not ready')
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):experiment(evidence,forbidden)
        captured=(stdout.getvalue()+stderr.getvalue()).encode()
        require(all(token not in captured and base64.b64encode(token) not in captured and token.hex().encode() not in captured for token in forbidden),'Credential in parent output')
        evidence['checks']['I09']['captured_parent_stdout_bytes']=len(stdout.getvalue());evidence['checks']['I09']['captured_parent_stderr_bytes']=len(stderr.getvalue())
        evidence['inputsAfter']=inputs();require(evidence['inputsBefore']==evidence['inputsAfter'],'Source/input changed')
        evidence['status']='PASS'
    except Exception as error:
        evidence['status']='ERROR';evidence['errorType']=type(error).__name__
        (CACHE/'last-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    evidence['elapsedSeconds']=time.monotonic()-begin;evidence['finishedAt']=datetime.now(timezone.utc).isoformat()
    encoded=json.dumps(evidence,indent=2).encode();require(all(token not in encoded and base64.b64encode(token) not in encoded and token.hex().encode() not in encoded for token in forbidden),'Credential in evidence')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as stream:stream.write(encoded+b'\n')
    print(json.dumps({'status':evidence['status'],'elapsedSeconds':evidence['elapsedSeconds'],'checks':{k:v['status'] for k,v in evidence.get('checks',{}).items()}}))
    return 0 if evidence['status']=='PASS' else 2
if __name__=='__main__':mp.freeze_support();raise SystemExit(main())
