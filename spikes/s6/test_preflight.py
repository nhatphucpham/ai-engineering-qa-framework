"""Real-process prerequisite rejection; no global crypto fallback execution."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent


class PreflightTests(unittest.TestCase):
    def probe(self,folder,prefix=''):
        code=('import sys,json,types;sys.path.insert(0,'+repr(str(HERE))+');'+prefix+
              'from preflight import crypto_inventory;result=crypto_inventory('+repr(str(folder))+');'
              'print(json.dumps({"result":result,"cryptoImported":"cryptography" in sys.modules,'
              '"backendImported":"_cffi_backend" in sys.modules}))')
        run=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(run.stderr,'')
        return json.loads(run.stdout)
    def metadata(self,folder,correct):
        for name,version in {'cryptography':'50.0.2','cffi':'2.1.1','pycparser':'3.12'}.items():
            path=Path(folder)/(name+'-fixture.dist-info');path.mkdir()
            (path/'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {version if correct else "0.0.0"}\n')
    def test_missing_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            value=self.probe(folder)
            self.assertFalse(value['result']['ready']);self.assertFalse(value['cryptoImported']);self.assertFalse(value['backendImported'])
    def test_mismatch_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            self.metadata(folder,False);value=self.probe(folder)
            self.assertFalse(value['result']['ready']);self.assertFalse(value['cryptoImported'])
    def test_incomplete_local_metadata_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            self.metadata(folder,True);value=self.probe(folder)
            self.assertFalse(value['result']['ready']);self.assertFalse(value['cryptoImported'])
    def test_already_loaded_outside_module_refused(self):
        deps=HERE.parents[1]/'.cache/s6/deps'
        value=self.probe(deps,'m=types.ModuleType("cryptography");m.__file__="C:/outside/global.py";sys.modules["cryptography"]=m;')
        self.assertFalse(value['result']['ready']);self.assertFalse(value['backendImported'])
    def test_pinned_local_module_paths_ready(self):
        deps=HERE.parents[1]/'.cache/s6/deps'
        value=self.probe(deps);self.assertTrue(value['result']['ready']);self.assertTrue(value['result']['local_paths'])


if __name__=='__main__':unittest.main()
