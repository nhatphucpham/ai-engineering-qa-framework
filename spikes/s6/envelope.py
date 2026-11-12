"""Synthetic envelope v1 using maintained AEAD; no authentication or QA read authority."""

import json
import os
import re
from paths import ROOT,CACHE,DEPS,Blocked
from preflight import require_crypto
require_crypto()
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',value):
        raise Blocked('E_CONTEXT')


def positive(value):
    if type(value) is not int or value<1:raise Blocked('E_CONTEXT')


def context(project,ref,version,kind='secret'):
    identifier(project);identifier(ref);positive(version)
    if kind not in ('secret','quarantine'):raise Blocked('E_CONTEXT')
    return {'envelopeVersion':'s6-envelope-1.0.0','kind':kind,'project':project,'ref':ref,'version':version}


def aad(scope,purpose,key_id=None):
    value={**scope,'purpose':purpose}
    if key_id is not None:value['keyId']=key_id
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def check_scope(scope):
    if (not isinstance(scope,dict) or set(scope)!={'envelopeVersion','kind','project','ref','version'}
        or scope['envelopeVersion']!='s6-envelope-1.0.0'):raise Blocked('E_CONTEXT')
    context(scope['project'],scope['ref'],scope['version'],scope['kind'])


class DummyKeys:
    """Only generated dummy material in process; production OS/key-store port is absent."""
    def __init__(self,values=None):self.values=dict(values or {})
    def generate(self,key_id):
        identifier(key_id)
        if key_id in self.values:raise Blocked('E_KEY_ID')
        self.values[key_id]=AESGCM.generate_key(bit_length=256)
    def get(self,key_id):
        identifier(key_id)
        value=self.values.get(key_id)
        if type(value) is not bytes or len(value)!=32:raise Blocked('E_KEY_UNAVAILABLE')
        return value


FIELDS={'scope','keyId','wrapNonce','wrappedKey','dataNonce','ciphertext'}


def validate(envelope,expected_scope):
    if not isinstance(envelope,dict) or set(envelope)!=FIELDS:raise Blocked('E_ENVELOPE')
    check_scope(expected_scope);check_scope(envelope['scope'])
    if envelope['scope']!=expected_scope:raise Blocked('E_CONTEXT')
    # Reconstruct expected context: numeric bool/integral float never alias version1.
    context(**{'project':expected_scope['project'],'ref':expected_scope['ref'],
               'version':expected_scope['version'],'kind':expected_scope['kind']})
    embedded=envelope['scope']
    if (set(embedded)!=set(expected_scope) or type(embedded['version']) is not int
        or embedded['envelopeVersion']!='s6-envelope-1.0.0'):raise Blocked('E_CONTEXT')
    identifier(envelope['keyId'])
    for name,length in (('wrapNonce',12),('wrappedKey',48),('dataNonce',12)):
        if type(envelope[name]) is not bytes or len(envelope[name])!=length:raise Blocked('E_ENVELOPE')
    if type(envelope['ciphertext']) is not bytes or not 16<=len(envelope['ciphertext'])<=65552:
        raise Blocked('E_ENVELOPE')


def seal(plaintext,scope,keys,key_id,wrap_nonce=None):
    if type(plaintext) is not bytes or not 1<=len(plaintext)<=65536:raise Blocked('E_PAYLOAD')
    check_scope(scope);identifier(key_id)
    dek=AESGCM.generate_key(bit_length=256)
    wrap_nonce=os.urandom(12) if wrap_nonce is None else wrap_nonce;data_nonce=os.urandom(12)
    if type(wrap_nonce) is not bytes or len(wrap_nonce)!=12:raise Blocked('E_NONCE')
    return {'scope':dict(scope),'keyId':key_id,'wrapNonce':wrap_nonce,
        'wrappedKey':AESGCM(keys.get(key_id)).encrypt(wrap_nonce,dek,aad(scope,'wrap',key_id)),
        'dataNonce':data_nonce,'ciphertext':AESGCM(dek).encrypt(data_nonce,plaintext,aad(scope,'payload'))}


def open_envelope(envelope,expected_scope,keys):
    validate(envelope,expected_scope)
    try:
        dek=AESGCM(keys.get(envelope['keyId'])).decrypt(envelope['wrapNonce'],envelope['wrappedKey'],
                                                     aad(expected_scope,'wrap',envelope['keyId']))
        return AESGCM(dek).decrypt(envelope['dataNonce'],envelope['ciphertext'],aad(expected_scope,'payload'))
    except (InvalidTag,ValueError):raise Blocked('E_INTEGRITY') from None


def rewrap(envelope,expected_scope,keys,new_key_id,wrap_nonce=None):
    validate(envelope,expected_scope);identifier(new_key_id)
    try:
        dek=AESGCM(keys.get(envelope['keyId'])).decrypt(envelope['wrapNonce'],envelope['wrappedKey'],
                                                     aad(expected_scope,'wrap',envelope['keyId']))
        # Verify payload integrity as well before changing its wrapper.
        AESGCM(dek).decrypt(envelope['dataNonce'],envelope['ciphertext'],aad(expected_scope,'payload'))
        nonce=os.urandom(12) if wrap_nonce is None else wrap_nonce
        if type(nonce) is not bytes or len(nonce)!=12:raise Blocked('E_NONCE')
        return {**envelope,'keyId':new_key_id,'wrapNonce':nonce,
                'wrappedKey':AESGCM(keys.get(new_key_id)).encrypt(nonce,dek,aad(expected_scope,'wrap',new_key_id))}
    except (InvalidTag,ValueError):raise Blocked('E_INTEGRITY') from None
