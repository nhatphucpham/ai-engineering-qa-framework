"""Private dummy-envelope diagnostic probe. Fixed JSON; never echoes fixture/key data."""
import base64
import hashlib
import json
from pathlib import Path
import sys
from preflight import crypto_inventory

def main():
    if not crypto_inventory()['ready']:
        print(json.dumps({'status':'blocked','code':'E_CRYPTO_NOT_READY'}));return 2
    from envelope import CACHE,Blocked,DummyKeys,AESGCM,open_envelope
    try:
        if len(sys.argv)!=3 or sys.argv[2] not in ('valid','missing','wrong','tamper','unsupported'):
            raise Blocked('E_INPUT')
        path=Path(sys.argv[1])
        if path.resolve().parent!=CACHE.resolve() or not path.name.startswith('probe-'):raise Blocked('E_INPUT')
        data=json.loads(path.read_text());scope=data['scope']
        keypath=Path(data['keyFile'])
        if keypath.resolve().parent!=CACHE.resolve() or not keypath.name.startswith('keys-'):raise Blocked('E_INPUT')
        record=json.loads(keypath.read_text())
        if record.get('kind')!='s6-dummy-keys-v1':raise Blocked('E_INPUT')
        keys=DummyKeys({name:base64.b64decode(value,validate=True) for name,value in record['keys'].items()})
        envelope={'scope':dict(scope),'keyId':data['keyId'],**{name:base64.b64decode(data[name],validate=True)
                  for name in ('wrapNonce','wrappedKey','dataNonce','ciphertext')}}
        mode=sys.argv[2]
        if mode=='missing':keys=DummyKeys()
        if mode=='wrong':keys=DummyKeys({envelope['keyId']:AESGCM.generate_key(bit_length=256)})
        if mode=='tamper':envelope['ciphertext']=bytes([envelope['ciphertext'][0]^1])+envelope['ciphertext'][1:]
        if mode=='unsupported':envelope['scope']['envelopeVersion']='unsupported'
        raw=open_envelope(envelope,scope,keys)
        print(json.dumps({'status':'opened','matches':hashlib.sha256(raw).hexdigest()==data['expectedSha256']}));return 0
    except Blocked as error:print(json.dumps({'status':'blocked','code':error.code}));return 2
    except Exception:print(json.dumps({'status':'blocked','code':'E_INPUT'}));return 2

if __name__=='__main__':raise SystemExit(main())
