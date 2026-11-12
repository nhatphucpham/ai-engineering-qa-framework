"""Version/path prerequisite checks only; no actual container capability claim."""

import importlib
import importlib.metadata
import importlib.machinery
import sys
import shutil
import subprocess
from pathlib import Path
import json

from paths import DEPS,Blocked

PINS={'cryptography':'50.0.2','cffi':'2.1.1','pycparser':'3.12'}


def crypto_inventory(deps=DEPS):
    deps=Path(deps).resolve()
    versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions(path=[str(deps)])}
    result={'versions':{name:versions.get(name) for name in PINS},'ready':False}
    if result['versions']!=PINS:return result
    for name in (*PINS,'_cffi_backend'):
        loaded=sys.modules.get(name)
        spec=importlib.machinery.PathFinder.find_spec(name,[str(deps)])
        if (spec is None or spec.origin is None or not Path(spec.origin).resolve().is_relative_to(deps)
            or loaded is not None and not Path(getattr(loaded,'__file__','')).resolve().is_relative_to(deps)):
            return result
    sys.path.insert(0,str(deps))
    try:
        modules=[importlib.import_module(name) for name in (*PINS,'_cffi_backend','cryptography.hazmat.bindings._rust')]
    except (ImportError,OSError,ValueError):return result
    finally:sys.path.pop(0)
    result['local_paths']=all(Path(module.__file__).resolve().is_relative_to(deps) for module in modules)
    result['loaded_versions']={name:module.__version__ for name,module in zip(PINS,modules)}
    result['ready']=(result['local_paths'] and result['loaded_versions']==PINS
                     and sys.version_info[:3]==(3,14,8) and sys.platform=='win32'
                     and modules[3].__version__==PINS['cffi'])
    return result


def require_crypto():
    if not crypto_inventory()['ready']:raise Blocked('E_CRYPTO_NOT_READY')
    sys.path.insert(0,str(DEPS))


def engine_inventory():
    names=('docker','podman','nerdctl','runc','crun','rootlesskit','slirp4netns')
    result={'windows_path':{name:bool(shutil.which(name)) for name in names},
            'scope':'PATH/common paths only; no daemon/engine/capability/image execution',
            'execution':'NOT RUN','ready':False}
    if shutil.which('wsl'):
        script='for x in docker podman nerdctl runc crun rootlesskit slirp4netns; do command -v "$x" || true; done; id -u; uname -r; ls /usr/bin/*podman* /usr/bin/*docker* /usr/local/bin/*podman* /usr/local/bin/*docker* 2>/dev/null || true'
        try:
            proc=subprocess.run(['wsl','-d','Ubuntu-24.04','--exec','sh','-c',script],capture_output=True,text=True,
                                timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
            result['wsl']={'exitcode':proc.returncode,'observations':proc.stdout.strip().splitlines()}
        except subprocess.TimeoutExpired:result['wsl']={'status':'DISCOVERY TIMEOUT'}
    return result


if __name__=='__main__':
    result=crypto_inventory()
    print(json.dumps({'status':'READY' if result['ready'] else 'NOT READY','crypto':result}))
    raise SystemExit(0 if result['ready'] else 2)
