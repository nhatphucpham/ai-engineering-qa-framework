"""Controlled dummy request diagnostic CLI, never emits credentials or session pairs."""
import json,sys
from pathlib import Path
from preflight_b import CACHE,inventory
def main():
    if not inventory()['ready']:
        print(json.dumps({'status':'blocked','code':'E_PREREQUISITES'}));return 2
    from identity import Identity,Denied
    api=None
    try:
        if len(sys.argv)!=3:raise Denied('E_INPUT')
        path=Path(sys.argv[2])
        if path.resolve().parent!=CACHE.resolve() or not path.name.startswith('probe-'):raise Denied('E_INPUT')
        body=json.loads(path.read_text());api=Identity(sys.argv[1]);api.dispatch(body['operation'],**body['body'])
        print(json.dumps({'status':'accepted'}));return 0
    except Denied as error:print(json.dumps({'status':'blocked','code':error.code}));return 2
    except Exception:print(json.dumps({'status':'blocked','code':'E_INPUT'}));return 2
    finally:
        if api:api.close()
if __name__=='__main__':raise SystemExit(main())
