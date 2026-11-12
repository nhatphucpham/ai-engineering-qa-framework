"""Trusted local model dump/restore only; no existing target or external archive API."""

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import uuid

from store_c import CapacityStore,sql,ROOT
from store_b import psycopg,dict_row
from local import CACHE,read_config,clean_environment,connect,command


def normalize(value):
    if isinstance(value,(bytes,bytearray,memoryview)):return {'bytea':bytes(value).hex()}
    if isinstance(value,(datetime,Decimal)):return str(value)
    if isinstance(value,dict):return {key:normalize(item) for key,item in value.items()}
    if isinstance(value,list):return [normalize(item) for item in value]
    return value


def fingerprint(store,schema):
    result={}
    with store.conn.transaction():
        store.conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        names=store.conn.execute('''SELECT table_name FROM information_schema.tables
            WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name''',(schema,)).fetchall()
        for item in names:
            name=item['table_name']
            rows=store.conn.execute(sql.SQL('SELECT * FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(name))).fetchall()
            encoded=sorted(json.dumps(normalize(row),sort_keys=True,separators=(',',':'),ensure_ascii=False) for row in rows)
            result[name]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}
    return result


def create_target():
    clean_environment()
    config=read_config()
    source=connect();source.close()  # Source identity confirms this disposable cluster before create.
    tag=uuid.uuid4().hex
    database='s2_restore_'+tag
    marker=uuid.uuid4().hex
    command('createdb','-h','127.0.0.1','-p',config['port'],'-U',config['user'],database)
    with psycopg.connect(host='127.0.0.1',port=config['port'],dbname=database,user=config['user'],password='',
        connect_timeout=5,options='-c timezone=UTC',autocommit=True) as conn:
        conn.execute('CREATE TABLE public.s2_identity(marker text PRIMARY KEY)')
        conn.execute('INSERT INTO public.s2_identity VALUES(%s)',(marker,))
    record={'kind':'s2c-disposable-restore-v1','database':database,'marker':marker,'clusterMarker':config['marker']}
    with (CACHE/('restore-'+tag+'.json')).open('x',encoding='utf-8') as stream:json.dump(record,stream)
    return database


def restore_connection(database):
    clean_environment()
    if not re.fullmatch(r's2_restore_[a-f0-9]{32}',database):raise ValueError('Restore target rejected')
    config=read_config()
    record=json.loads((CACHE/('restore-'+database.removeprefix('s2_restore_')+'.json')).read_text())
    if (record.get('kind')!='s2c-disposable-restore-v1' or record.get('database')!=database
        or record.get('clusterMarker')!=config['marker']):raise ValueError('Restore marker rejected')
    conn=psycopg.connect(host='127.0.0.1',port=config['port'],dbname=database,user=config['user'],password='',
        connect_timeout=5,options='-c timezone=UTC -c statement_timeout=15000 -c lock_timeout=10000',autocommit=True)
    if conn.execute('SELECT marker FROM public.s2_identity').fetchone()!=(record['marker'],):
        conn.close();raise ValueError('Restore identity mismatch')
    return conn


def dump(schema,path):
    if not re.fullmatch(r's2_[a-f0-9]{32}',schema) or path.exists() or path.resolve().parent!=CACHE.resolve():
        raise ValueError('Dump destination rejected')
    clean_environment();config=read_config()
    command('pg_dump','-h','127.0.0.1','-p',config['port'],'-U',config['user'],'--dbname',config['database'],
        '--format=custom','--schema',schema,'--no-owner','--no-privileges','--file',path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore(database,schema,path,expected_sha256):
    if not re.fullmatch(r's2_[a-f0-9]{32}',schema) or path.resolve().parent!=CACHE.resolve():
        raise ValueError('Restore archive/scope rejected')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256:
        raise ValueError('Archive differs from caller-held dump hash')
    conn=restore_connection(database)
    try:
        if conn.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(schema,)).fetchone():
            raise ValueError('Existing restore namespace refused')
    finally:conn.close()
    config=read_config()
    return command('pg_restore','-h','127.0.0.1','-p',config['port'],'-U',config['user'],'--dbname',database,
        '--single-transaction','--exit-on-error','--no-owner','--no-privileges',path)


class RestoredStore(CapacityStore):
    def __init__(self,database,schema):
        if not re.fullmatch(r's2_[a-f0-9]{32}',schema):raise ValueError('Restore schema rejected')
        self.conn=restore_connection(database)
        self.conn.row_factory=dict_row
        self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
        if self.conn.execute('SELECT version FROM capacity_identity').fetchone()!={'version':'s2c-1.0.0'}:
            self.close();raise ValueError('Wrong restored model')
