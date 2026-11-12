"""Actual AEAD/DB synthetic storage experiment; never prints dummy secrets/keys."""

from preflight import crypto_inventory,engine_inventory
import json
import sys
crypto=crypto_inventory()
if not crypto['ready']:
    print(json.dumps({'status':'NOT READY','crypto':crypto,'execution':'NOT RUN'}));raise SystemExit(2)

import base64
import copy
import contextlib
import io
from datetime import datetime,timezone
import hashlib
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import time
import traceback
import uuid

from envelope import ROOT,CACHE,Blocked,DummyKeys,context,seal,open_envelope,AESGCM,aad
from vault import Vault
sys.path.insert(0,str(ROOT/'spikes/s2c'))
from backup import fingerprint,create_target,restore_connection
from local import read_config,command,inventory as db_inventory,stop,start
from psycopg import sql


def require(value,message):
    if not value:raise AssertionError(message)


def denied(action):
    try:action()
    except Blocked as error:return error.code
    raise AssertionError('Expected fixed-code denial did not occur')


def key_file(keys):
    path=CACHE/('keys-'+uuid.uuid4().hex+'.json')
    with path.open('x',encoding='utf-8') as stream:
        json.dump({'kind':'s6-dummy-keys-v1','keys':{name:base64.b64encode(value).decode() for name,value in keys.values.items()}},stream)
    return path


def load_keys(path):
    path=Path(path)
    if path.resolve().parent!=CACHE.resolve() or not path.name.startswith('keys-'):raise Blocked('E_KEY_UNAVAILABLE')
    data=json.loads(path.read_text())
    if data.get('kind')!='s6-dummy-keys-v1':raise Blocked('E_KEY_UNAVAILABLE')
    return DummyKeys({name:base64.b64decode(value,validate=True) for name,value in data['keys'].items()})


def update_child(schema,anchor,keypath,plaintext,gate,pipe):
    vault=Vault(schema)
    try:
        gate.wait(timeout=20)
        try:
            result=vault.write(anchor['project'],anchor['ref'],plaintext,load_keys(keypath),'masterA',
                               anchor['version'],anchor['epoch'])
            pipe.send({'status':'accepted','anchor':result})
        except Blocked as error:pipe.send({'status':'rejected','code':error.code})
    finally:vault.close();pipe.close()


def recover_child(schema,database,keypath,anchor,expected,pipe):
    vault=Vault(schema,connection=restore_connection(database))
    try:
        try:
            raw=vault.exercise_private_open(anchor,load_keys(keypath))
            pipe.send({'status':'opened','matches':raw==expected})
        except Blocked as error:pipe.send({'status':'blocked','code':error.code})
    finally:vault.close();pipe.close()


def child_call(target,args):
    parent,child=mp.Pipe();proc=mp.Process(target=target,args=(*args,child));proc.start();child.close()
    try:
        require(parent.poll(25),'Child did not report a safe result');result=parent.recv()
        proc.join(10);require(proc.exitcode==0,'Child failed');return result
    finally:
        if proc.is_alive():proc.kill();proc.join(10)
        parent.close()


def scan_rows(vault,forbidden):
    raw=b''
    for name in ('projects','heads','encrypted_versions','audit','key_identity','nonce_history'):
        rows=vault.conn.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(name))).fetchall()
        for row in rows:
            for value in row.values():
                raw+=bytes(value) if isinstance(value,(bytes,bytearray,memoryview)) else str(value).encode()
    require(all(item not in raw for item in forbidden),'Raw dummy material found in database rows')


def experiment(evidence,forbidden):
    schema='s6_'+uuid.uuid4().hex;evidence['schema']=schema
    vault=Vault(schema,create=True);checks=evidence['checks']={}
    keys=DummyKeys();keys.generate('masterA');keys.generate('masterB')
    secret=b'synthetic-secret-'+os.urandom(20).hex().encode();new_secret=b'synthetic-rotated-'+os.urandom(20).hex().encode()
    forbidden.extend([secret,new_secret,*keys.values.values()])
    try:
        scope=context('projectA','probe',1);envelope=seal(secret,scope,keys,'masterA')
        require(open_envelope(envelope,scope,keys)==secret,'AEAD round-trip failed')
        checks['K01']={'status':'PASS','local_crypto':crypto,'algorithm':'AESGCM256 envelope v1','roundtrip':True}
        probes=[]
        for name in ('wrapNonce','wrappedKey','dataNonce','ciphertext'):
            bad=copy.deepcopy(envelope);value=bytearray(bad[name]);value[0]^=1;bad[name]=bytes(value)
            probes.append({'field':name,'code':denied(lambda:open_envelope(bad,scope,keys))})
        for field,value in (('project','projectB'),('ref','another'),('version',2),('version',True),('version',1.0),('kind','quarantine')):
            bad=copy.deepcopy(envelope);bad['scope'][field]=value
            probes.append({'field':field,'code':denied(lambda:open_envelope(bad,scope,keys))})
        for value in ('s6-envelope-999.0.0','',1,None):
            bad=copy.deepcopy(envelope);bad['scope']['envelopeVersion']=value
            probes.append({'field':'envelopeVersion','code':denied(lambda:open_envelope(bad,scope,keys))})
        bad=copy.deepcopy(envelope);bad['keyId']='masterB';denied(lambda:open_envelope(bad,scope,keys))
        checks['K02']={'status':'PASS','tamper_probes':probes,'key_id_substitution_rejected':True}
        missing=denied(lambda:open_envelope(envelope,scope,DummyKeys()))
        wrong=denied(lambda:open_envelope(envelope,scope,DummyKeys({'masterA':AESGCM.generate_key(bit_length=256)})))
        checks['K03']={'status':'PASS','missing_key':missing,'wrong_key':wrong}
        vault.project('projectA');vault.project('projectB')
        anchor=vault.write('projectA','provider',secret,keys,'masterA')
        require(vault.exercise_private_open(anchor,keys)==secret,'Stored dummy did not decrypt')
        for field in ('version','epoch'):
            for value in (True,1.0):
                denied(lambda:vault.exercise_private_open({**anchor,field:value},keys))
        stored=vault.envelope('projectA','provider',1)
        foreign_anchors=[vault.write('projectB','other',secret,keys,'masterA'),
                         vault.write('projectA','other',secret,keys,'masterA')]
        swaps=[]
        class RestoreTamper(Exception):pass
        for foreign_anchor in foreign_anchors:
            foreign=vault.envelope(foreign_anchor['project'],foreign_anchor['ref'],1)
            for field in ('payload','wrappedKey'):
                try:
                    with vault.conn.transaction():
                        if field=='payload':
                            vault.conn.execute('''UPDATE encrypted_versions SET ciphertext=%s,data_nonce=%s
                                WHERE project='projectA' AND ref='provider' AND version=1''',
                                (foreign['ciphertext'],foreign['dataNonce']))
                        else:
                            vault.conn.execute('''UPDATE encrypted_versions SET wrapped_key=%s
                                WHERE project='projectA' AND ref='provider' AND version=1''',(foreign['wrappedKey'],))
                        code=denied(lambda:vault.exercise_private_open(anchor,keys))
                        swaps.append({'foreign_project':foreign_anchor['project'],'foreign_ref':foreign_anchor['ref'],
                                      'field':field,'code':code})
                        raise RestoreTamper()
                except RestoreTamper:pass
                require(vault.envelope('projectA','provider',1)==stored,'Tamper transaction was not rolled back')
        checks['K02']['db_cross_scope_swaps']=swaps
        dek=AESGCM(keys.get('masterA')).decrypt(stored['wrapNonce'],stored['wrappedKey'],aad(stored['scope'],'wrap','masterA'))
        forbidden.append(dek);scan_rows(vault,forbidden)
        checks['D01']={'status':'PASS','raw_plaintext_or_keys_in_rows':False,'ciphertext_length':len(stored['ciphertext'])}
        path=key_file(keys);gate=mp.Barrier(2);children=[];pipes=[]
        for _ in range(2):
            parent,child=mp.Pipe();proc=mp.Process(target=update_child,args=(schema,anchor,path,new_secret,gate,child))
            proc.start();child.close();children.append(proc);pipes.append(parent)
        try:
            outcomes=[]
            for pipe in pipes:require(pipe.poll(25),'Rotation process timeout');outcomes.append(pipe.recv())
            for proc in children:proc.join(10);require(proc.exitcode==0,'Rotation process failed')
        finally:
            for proc in children:
                if proc.is_alive():proc.kill();proc.join(10)
            for pipe in pipes:pipe.close()
        require(sum(row['status']=='accepted' for row in outcomes)==1,'Concurrent rotation CAS not unique')
        current=next(row['anchor'] for row in outcomes if row['status']=='accepted')
        denied(lambda:vault.exercise_private_open(anchor,keys));require(vault.exercise_private_open(current,keys)==new_secret,'Rotated read mismatch')
        require(vault.envelope('projectA','provider',1)==stored,'Prior immutable ciphertext overwritten')
        checks['D02']={'status':'PASS','concurrent_process_results':outcomes,'old_anchor_rejected':True,'old_ciphertext_preserved':True}
        before=vault.envelope('projectA','provider',2);audit_before=vault.conn.execute('SELECT count(*) AS n FROM audit').fetchone()['n']
        nonce_before=vault.conn.execute('SELECT count(*) AS n FROM nonce_history').fetchone()['n']
        class Injected(Exception):pass
        def rollback():raise Injected()
        try:vault.rewrap(current,keys,'masterB',before_commit=rollback)
        except Injected:pass
        require(vault.envelope('projectA','provider',2)==before,'Failed rewrap changed wrapper')
        require(vault.conn.execute('SELECT count(*) AS n FROM audit').fetchone()['n']==audit_before,'Failed rewrap published audit')
        require(vault.conn.execute('SELECT count(*) AS n FROM nonce_history').fetchone()['n']==nonce_before+1,'Nonce reservation recycled on rollback')
        vault.rewrap(current,keys,'masterB');after=vault.envelope('projectA','provider',2)
        require(before['ciphertext']==after['ciphertext'] and before['dataNonce']==after['dataNonce'] and before['wrappedKey']!=after['wrappedKey'],'Rewrap changed payload/failed wrapper change')
        denied(lambda:vault.rewrap(current,keys,'masterA',expected_revision=1))
        require(vault.exercise_private_open(current,DummyKeys({'masterB':keys.get('masterB')}))==new_secret,'Selected rewrapped row still needs old KEK')
        # Used nonce cannot return after rewrap away/back; committed reservations survive DB restart.
        fixed=os.urandom(12);forced=Vault(schema,nonce_source=lambda _n:fixed)
        try:
            forced_anchor=forced.write('projectA','nonceProbe',secret,keys,'masterA')
            forced.rewrap(forced_anchor,keys,'masterB')
            denied(lambda:forced.rewrap(forced_anchor,keys,'masterA',expected_revision=2))
        finally:forced.close()
        alias=DummyKeys({**keys.values,'masterAlias':keys.get('masterA')})
        denied(lambda:vault.write('projectA','aliasProbe',secret,alias,'masterAlias'))
        class ChangingKeys:
            def __init__(self):self.calls={}
            def get(self,key_id):
                self.calls[key_id]=self.calls.get(key_id,0)+1
                return keys.get(key_id if self.calls[key_id]==1 else ('masterB' if key_id=='masterA' else 'masterA'))
        changing=ChangingKeys()
        pinned=vault.write('projectA','snapshotProbe',secret,changing,'masterA')
        require(changing.calls=={'masterA':1} and vault.exercise_private_open(pinned,keys)==secret,'Write did not pin exact registered key bytes')
        changing=ChangingKeys();vault.rewrap(pinned,changing,'masterB')
        require(changing.calls=={'masterA':1,'masterB':1} and vault.exercise_private_open(pinned,keys)==secret,'Rewrap did not pin both key versions')
        checks['D03']={'status':'PASS','payload_unchanged':True,'rollback_burned_nonce':True,
            'rewrap_away_back_nonce_reuse_rejected':True,'key_alias_rejected':True,'changing_provider_snapshot_verified':True}
        revoked=vault.revoke(current);denied(lambda:vault.exercise_private_open(current,keys));denied(lambda:vault.exercise_private_open(revoked,keys))
        vault.close();stop();start();vault=Vault(schema)
        denied(lambda:vault.exercise_private_open(current,keys))
        forced=Vault(schema,nonce_source=lambda _n:fixed)
        try:denied(lambda:forced.rewrap(forced_anchor,keys,'masterA',expected_revision=2))
        finally:forced.close()
        checks['D04']={'status':'PASS','revoked_anchor':revoked,'restart_did_not_revive':True,'nonce_history_survived_restart':True}
        raw=b'synthetic-secret-log:'+secret;forbidden.append(raw)
        log_anchor=vault.quarantine('projectA','rawLog',raw,keys,'masterB')
        content_codes=[]
        for role in ('Admin','Owner','Runner','Viewer'):
            for channel in ('read','export','stream','attachment','source'):
                content_codes.append(denied(lambda:vault.qa_content('projectA','rawLog',role,channel,redacted=True,authorized=True)))
        require(content_codes==['E_RESTRICTED']*20,'A QA route released raw content')
        denied(lambda:vault.exercise_private_open(log_anchor,keys));scan_rows(vault,forbidden)
        checks['Q01']={'status':'PASS','ordinary_routes_denied':20,'fake_redaction_or_authorization_ignored':True,'quarantine_encrypted':True}
        # A separate non-revoked row is recovered from an actual schema archive plus external dummy keys.
        recover_anchor=vault.write('projectB','recovery',new_secret,keys,'masterB')
        config=read_config();archive=CACHE/('s6-'+schema+'.dump')
        command('pg_dump','-h','127.0.0.1','-p',config['port'],'-U',config['user'],'--dbname',config['database'],
                '--schema',schema,'--format=custom','--no-owner','--no-privileges','--file',archive)
        archive_bytes=archive.read_bytes();require(all(value not in archive_bytes for value in forbidden),'Raw dummy material in DB archive')
        before_restore=fingerprint(vault,schema);database=create_target()
        command('pg_restore','-h','127.0.0.1','-p',config['port'],'-U',config['user'],'--dbname',database,
                '--single-transaction','--exit-on-error','--no-owner','--no-privileges',archive)
        keypath=key_file(keys)
        recovered=child_call(recover_child,(schema,database,keypath,recover_anchor,new_secret))
        require(recovered=={'status':'opened','matches':True},'Actual child recovery failed')
        restored=Vault(schema,connection=restore_connection(database))
        try:
            require(fingerprint(restored,schema)==before_restore,'Restored encrypted metadata mismatch')
            denied(lambda:restored.write('projectB','newRef',secret,keys,'masterB'))
            denied(lambda:restored.rewrap(recover_anchor,keys,'masterA'))
            newest=vault.revoke(recover_anchor)
            denied(lambda:restored.exercise_private_open(newest,keys))
        finally:restored.close()
        wrongpath=key_file(DummyKeys({'masterB':AESGCM.generate_key(bit_length=256)}))
        wrong_recovery=child_call(recover_child,(schema,database,wrongpath,recover_anchor,new_secret))
        require(wrong_recovery['status']=='blocked','Wrong external recovery key succeeded')
        scan_rows(vault,forbidden)
        checks['R01']={'status':'PASS','restore_database':database,'archive_sha256':hashlib.sha256(archive_bytes).hexdigest(),
            'archive_excludes_raw_material':True,'separate_dummy_key_file':True,'child_recovered':recovered,
            'wrong_key_child':wrong_recovery,'table_fingerprints_match':True,'restored_writes_rejected':True,
            'newer_independent_policy_anchor_rejected_old_restore':True}
        audit=vault.conn.execute('SELECT * FROM audit ORDER BY sequence').fetchall()
        encoded=json.dumps(audit).encode();require(all(value not in encoded for value in forbidden),'Raw material in audit')
        probe=CACHE/('probe-'+uuid.uuid4().hex+'.json')
        fixture={'scope':scope,'keyId':envelope['keyId'],'keyFile':str(key_file(keys)),
                 'expectedSha256':hashlib.sha256(secret).hexdigest(),**{name:base64.b64encode(envelope[name]).decode()
                 for name in ('wrapNonce','wrappedKey','dataNonce','ciphertext')}}
        probe.write_text(json.dumps(fixture),encoding='utf-8')
        captures=[]
        for mode in ('valid','missing','wrong','tamper','unsupported','invalid-mode'):
            run=subprocess.run([sys.executable,'-B',str(ROOT/'spikes/s6/probe_cli.py'),str(probe),mode],
                               capture_output=True,text=True,timeout=15)
            captured=(run.stdout+run.stderr).encode()
            require(all(token not in captured and base64.b64encode(token) not in captured and token.hex().encode() not in captured
                        for token in forbidden),'Raw material in captured CLI output')
            require(run.stderr=='' and run.returncode==(0 if mode=='valid' else 2),'CLI outcome/error channel mismatch')
            value=json.loads(run.stdout)
            require(value=={'status':'opened','matches':True} if mode=='valid' else
                    set(value)=={'status','code'} and value['status']=='blocked' and value['code'] in
                    ('E_KEY_UNAVAILABLE','E_INTEGRITY','E_CONTEXT','E_INPUT'),'Unexpected diagnostic shape')
            captures.append({'mode':mode,'exitcode':run.returncode,'status':value['status'],'stdout_bytes':len(run.stdout.encode()),
                             'stderr_bytes':len(run.stderr.encode()),'fixed_code':value.get('code')})
        checks['O01']={'status':'PASS','audit_rows':len(audit),'captured_cli_cases':captures,
                       'fixed_code_diagnostics_only':True,'raw_material_in_committed_output':False}
    finally:vault.close()


def inputs():
    paths=set()
    for name in ('qa_core','schemas','spikes/s2','spikes/s2b','spikes/s2c','spikes/s6'):
        paths.update(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.add(ROOT/'docs/S6-A-PROTOCOL.md')
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: py -3 -B spikes/s6/run_s6.py docs/s6-results/<new-id>.json')
    destination=(ROOT/sys.argv[1]).resolve()
    if destination.parent!=(ROOT/'docs/s6-results').resolve() or destination.suffix!='.json' or destination.exists():
        raise SystemExit('Use a new evidence destination under docs/s6-results')
    evidence={'evidenceVersion':'s6-a-1.0.0','classification':'synthetic-only',
        'baseline':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'startedAt':datetime.now(timezone.utc).isoformat(),'command':'py -3 -B spikes/s6/run_s6.py '+sys.argv[1],
        'crypto':crypto,'database_preflight':db_inventory(),'s4_prerequisites':engine_inventory(),
        'inputsBefore':inputs(),'status':'RUNNING','limits':['Private operator storage harness; no authenticated QA/broker/session API',
            'S4 engine/physical containment/cleanup NOT RUN','Dummy external key file is not OS keystore/production key backup',
            'Restored vault read-only; latest trustworthy nonce/policy reconciliation not implemented','Full S6/P3-B/P4-B remain open']}
    begin=time.monotonic();forbidden=[];captured_out=io.StringIO();captured_err=io.StringIO()
    try:
        require(evidence['database_preflight']['toolchainReady'],'DB prerequisites NOT READY')
        with contextlib.redirect_stdout(captured_out),contextlib.redirect_stderr(captured_err):
            experiment(evidence,forbidden)
        captured=(captured_out.getvalue()+captured_err.getvalue()).encode()
        require(all(token not in captured and base64.b64encode(token) not in captured and token.hex().encode() not in captured
                    for token in forbidden),'Raw material in captured harness output')
        evidence['checks']['O01']['captured_harness_stdout_bytes']=len(captured_out.getvalue().encode())
        evidence['checks']['O01']['captured_harness_stderr_bytes']=len(captured_err.getvalue().encode())
        evidence['inputsAfter']=inputs()
        require(evidence['inputsBefore']==evidence['inputsAfter'],'Source/input changed during run')
        evidence['status']='PASS'
    except Exception as error:
        evidence['status']='ERROR';evidence['errorType']=type(error).__name__
        (CACHE/'last-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    evidence['elapsedSeconds']=time.monotonic()-begin;evidence['finishedAt']=datetime.now(timezone.utc).isoformat()
    encoded=json.dumps(evidence,indent=2).encode()
    require(all(value not in encoded and base64.b64encode(value) not in encoded and value.hex().encode() not in encoded for value in forbidden),'Raw dummy material in evidence')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(encoded+b'\n')
    print(json.dumps({'status':evidence['status'],'elapsedSeconds':evidence['elapsedSeconds'],
                     'checks':{key:value['status'] for key,value in evidence.get('checks',{}).items()}}))
    return 0 if evidence['status']=='PASS' else 2


if __name__=='__main__':mp.freeze_support();raise SystemExit(main())
