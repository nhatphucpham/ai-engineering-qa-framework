"""Only local experiment origins; missing library never falls back globally."""
from pathlib import Path
import importlib,importlib.metadata,importlib.machinery,json,sys
ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'.cache/s6b';DEPS=CACHE/'deps'
PINS={'argon2-cffi':'25.1.0','argon2-cffi-bindings':'26.1.0','cffi':'2.1.1','pycparser':'3.12'}

def inventory(deps=DEPS):
    deps=Path(deps).resolve()
    versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions(path=[str(deps)])}
    result={'versions':{name:versions.get(name) for name in PINS},'ready':False}
    if result['versions']!=PINS:return result
    names=('argon2','_argon2_cffi_bindings','cffi','pycparser','_cffi_backend')
    for name in names:
        loaded=sys.modules.get(name);spec=importlib.machinery.PathFinder.find_spec(name,[str(deps)])
        if (spec is None or not spec.origin or not Path(spec.origin).resolve().is_relative_to(deps)
            or loaded is not None and not Path(getattr(loaded,'__file__','')).resolve().is_relative_to(deps)):return result
    sys.path.insert(0,str(deps))
    try:modules=[importlib.import_module(name) for name in (*names,'_argon2_cffi_bindings._ffi')]
    except (ImportError,OSError,ValueError):return result
    finally:sys.path.pop(0)
    result['local_paths']=all(Path(m.__file__).resolve().is_relative_to(deps) for m in modules)
    result['ready']=(result['local_paths'] and sys.version_info[:3]==(3,14,8) and sys.platform=='win32'
                     and modules[2].__version__==PINS['cffi'] and modules[4].__version__==PINS['cffi'])
    return result

if __name__=='__main__':
    value=inventory();print(json.dumps({'status':'READY' if value['ready'] else 'NOT READY','details':value}));raise SystemExit(0 if value['ready'] else 2)
