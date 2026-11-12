"""Private operator-only synthetic vault, not a server/broker/authenticated QA API."""

from pathlib import Path
import re
import sys
import os
import hashlib

from envelope import ROOT,Blocked,DummyKeys,identifier,positive,context,seal,open_envelope,rewrap
sys.path.insert(0,str(ROOT/'spikes/s2'))
from local import connect
sys.path.insert(0,str(ROOT/'.cache/s2/deps'))
from psycopg import sql
from psycopg.rows import dict_row
import psycopg


class Vault:
    def __init__(self,schema,create=False,connection=None,nonce_source=os.urandom):
        if not re.fullmatch(r's6_[a-f0-9]{32}',schema):raise Blocked('E_SCHEMA')
        self.recovery_read_only=connection is not None
        self.nonce_source=nonce_source
        self.conn=connection or connect();self.conn.row_factory=dict_row;self.schema=schema
        if create:
            with self.conn.transaction():
                self.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
                self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
                self.conn.execute((Path(__file__).parent/'schema.sql').read_text())
        else:self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
        if self.conn.execute('SELECT version FROM model_identity').fetchone()!={'version':'s6a-1.0.0'}:
            self.close();raise Blocked('E_SCHEMA')
    def close(self):self.conn.close()
    def writable(self):
        if self.recovery_read_only:raise Blocked('E_RECOVERY_READ_ONLY')
    def project(self,name):
        self.writable()
        identifier(name);self.conn.execute('INSERT INTO projects(id) VALUES(%s)',(name,))
    def _project(self,name):
        identifier(name)
        row=self.conn.execute('SELECT * FROM projects WHERE id=%s FOR UPDATE',(name,)).fetchone()
        if row is None or not row['enabled']:raise Blocked('E_POLICY')
    def _head(self,project,ref,version,epoch):
        identifier(ref);positive(version);positive(epoch);self._project(project)
        row=self.conn.execute('SELECT * FROM heads WHERE project=%s AND ref=%s FOR UPDATE',(project,ref)).fetchone()
        if row is None or not row['enabled'] or (row['version'],row['epoch'])!=(version,epoch):raise Blocked('E_POLICY')
        return row
    def _save(self,envelope,revision=1):
        scope=envelope['scope']
        self.conn.execute('INSERT INTO encrypted_versions VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (scope['project'],scope['ref'],scope['version'],scope['kind'],envelope['keyId'],envelope['wrapNonce'],
             envelope['wrappedKey'],envelope['dataNonce'],envelope['ciphertext'],revision))
    def reserve_nonce(self,keys,key_id):
        self.writable();identifier(key_id)
        material=keys.get(key_id)
        tag=hashlib.sha256(material).digest();nonce=self.nonce_source(12)
        if type(nonce) is not bytes or len(nonce)!=12:raise Blocked('E_NONCE')
        # Independent committed reservation survives outer content rollback. Never recycle a used nonce.
        other=connect()
        try:
            other.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(self.schema)))
            with other.transaction():
                other.execute('INSERT INTO key_identity VALUES(%s,%s) ON CONFLICT(key_id) DO NOTHING',(key_id,tag))
                if other.execute('SELECT key_tag FROM key_identity WHERE key_id=%s',(key_id,)).fetchone()!=(tag,):
                    raise Blocked('E_KEY_ID')
                other.execute('INSERT INTO nonce_history VALUES(%s,%s)',(key_id,nonce))
        except psycopg.errors.UniqueViolation:raise Blocked('E_NONCE_REUSE') from None
        finally:other.close()
        return nonce,material
    def pinned_key(self,keys,key_id):
        material=keys.get(key_id)
        record=self.conn.execute('SELECT key_tag FROM key_identity WHERE key_id=%s',(key_id,)).fetchone()
        if record is None or bytes(record['key_tag'])!=hashlib.sha256(material).digest():raise Blocked('E_KEY_ID')
        return material
    @staticmethod
    def anchor(value):
        if not isinstance(value,dict) or set(value)!={'project','ref','version','epoch'}:raise Blocked('E_CONTEXT')
        identifier(value['project']);identifier(value['ref']);positive(value['version']);positive(value['epoch'])
    def _audit(self,project,ref,version,epoch,op):
        self.conn.execute('INSERT INTO audit(project,ref,version,epoch,operation) VALUES(%s,%s,%s,%s,%s)',
                          (project,ref,version,epoch,op))
    def write(self,project,ref,plaintext,keys,key_id,expected_version=0,expected_epoch=0,kind='secret'):
        self.writable()
        identifier(ref)
        if any(type(value) is not int or value<0 for value in (expected_version,expected_epoch)):raise Blocked('E_CONTEXT')
        with self.conn.transaction():
            self._project(project)
            head=self.conn.execute('SELECT * FROM heads WHERE project=%s AND ref=%s FOR UPDATE',(project,ref)).fetchone()
            if head is None:
                if (expected_version,expected_epoch)!=(0,0):raise Blocked('E_POLICY')
                version=epoch=1
                self.conn.execute('INSERT INTO heads VALUES(%s,%s,1,1,true)',(project,ref))
            else:
                if not head['enabled'] or (head['version'],head['epoch'])!=(expected_version,expected_epoch):raise Blocked('E_POLICY')
                version=head['version']+1;epoch=head['epoch']+1
                self.conn.execute('UPDATE heads SET version=%s,epoch=%s WHERE project=%s AND ref=%s',(version,epoch,project,ref))
            scope=context(project,ref,version,kind)
            nonce,material=self.reserve_nonce(keys,key_id)
            envelope=seal(plaintext,scope,DummyKeys({key_id:material}),key_id,nonce);self._save(envelope)
            self._audit(project,ref,version,epoch,'write' if kind=='secret' else 'quarantine')
            return {'project':project,'ref':ref,'version':version,'epoch':epoch}
    def envelope(self,project,ref,version):
        row=self.conn.execute('SELECT * FROM encrypted_versions WHERE project=%s AND ref=%s AND version=%s',
                              (project,ref,version)).fetchone()
        if row is None:raise Blocked('E_CONTEXT')
        return {'scope':context(project,ref,version,row['kind']),'keyId':row['key_id'],
            'wrapNonce':bytes(row['wrap_nonce']),'wrappedKey':bytes(row['wrapped_key']),
            'dataNonce':bytes(row['data_nonce']),'ciphertext':bytes(row['ciphertext'])}
    def exercise_private_open(self,anchor,keys):
        # Test-only operator path. Never route QA/client requests to this method.
        self.anchor(anchor)
        with self.conn.transaction():
            self._head(**anchor)
            envelope=self.envelope(anchor['project'],anchor['ref'],anchor['version'])
            if envelope['scope']['kind']!='secret':raise Blocked('E_RESTRICTED')
            key_id=envelope['keyId'];material=self.pinned_key(keys,key_id)
            return open_envelope(envelope,context(anchor['project'],anchor['ref'],anchor['version']),DummyKeys({key_id:material}))
    def revoke(self,anchor):
        self.writable()
        self.anchor(anchor)
        with self.conn.transaction():
            self._head(**anchor)
            self.conn.execute('UPDATE heads SET enabled=false,epoch=epoch+1 WHERE project=%s AND ref=%s',
                              (anchor['project'],anchor['ref']))
            self._audit(anchor['project'],anchor['ref'],anchor['version'],anchor['epoch']+1,'revoke')
            return {**anchor,'epoch':anchor['epoch']+1}
    def rewrap(self,anchor,keys,new_key_id,expected_revision=1,before_commit=lambda:None):
        self.writable()
        self.anchor(anchor);positive(expected_revision)
        with self.conn.transaction():
            self._head(**anchor)
            row=self.conn.execute('SELECT wrapping_revision FROM encrypted_versions WHERE project=%s AND ref=%s AND version=%s FOR UPDATE',
                                  (anchor['project'],anchor['ref'],anchor['version'])).fetchone()
            if row['wrapping_revision']!=expected_revision:raise Blocked('E_REVISION')
            old=self.envelope(anchor['project'],anchor['ref'],anchor['version'])
            old_material=self.pinned_key(keys,old['keyId'])
            nonce,new_material=self.reserve_nonce(keys,new_key_id)
            if old['keyId']==new_key_id and old_material!=new_material:raise Blocked('E_KEY_ID')
            snapshot=DummyKeys({old['keyId']:old_material,new_key_id:new_material})
            new=rewrap(old,old['scope'],snapshot,new_key_id,nonce)
            self.conn.execute('''UPDATE encrypted_versions SET key_id=%s,wrap_nonce=%s,wrapped_key=%s,wrapping_revision=wrapping_revision+1
                WHERE project=%s AND ref=%s AND version=%s''',(new['keyId'],new['wrapNonce'],new['wrappedKey'],
                anchor['project'],anchor['ref'],anchor['version']))
            self._audit(anchor['project'],anchor['ref'],anchor['version'],anchor['epoch'],'rewrap');before_commit()
    def quarantine(self,project,ref,raw,keys,key_id):return self.write(project,ref,raw,keys,key_id,kind='quarantine')
    def qa_content(self,project,ref,role,channel,**untrusted_labels):
        # Closed boundary for secret/raw taint, not a role-authentication implementation.
        # Labels cannot cause key access or decryption, including claims of redaction.
        raise Blocked('E_RESTRICTED')
