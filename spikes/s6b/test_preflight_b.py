"""Real-process prerequisite rejection, before any Argon2/global import."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
PINS={'argon2-cffi':'25.1.0','argon2-cffi-bindings':'26.1.0','cffi':'2.1.1','pycparser':'3.12'}

class PreflightBTests(unittest.TestCase):
    def probe(self,folder,prefix=''):
        code=('import sys,json,types;sys.path.insert(0,'+repr(str(HERE))+');'+prefix+
              'from preflight_b import inventory;result=inventory('+repr(str(folder))+');'
              'print(json.dumps({"result":result,"argonImported":"argon2" in sys.modules,'
              '"backendImported":"_cffi_backend" in sys.modules}))')
        run=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stderr,'')
        return json.loads(run.stdout)
    def metadata(self,folder,correct):
        for name,version in PINS.items():
            path=Path(folder)/(name+'-fixture.dist-info');path.mkdir()
            (path/'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {version if correct else "0.0.0"}\n')
    def test_missing_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            value=self.probe(folder);self.assertFalse(value['result']['ready'])
            self.assertFalse(value['argonImported']);self.assertFalse(value['backendImported'])
    def test_mismatch_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            self.metadata(folder,False);value=self.probe(folder)
            self.assertFalse(value['result']['ready']);self.assertFalse(value['argonImported'])
    def test_incomplete_local_metadata_does_not_import_global(self):
        with tempfile.TemporaryDirectory() as folder:
            self.metadata(folder,True);value=self.probe(folder)
            self.assertFalse(value['result']['ready']);self.assertFalse(value['argonImported'])
    def test_already_loaded_outside_module_refused(self):
        value=self.probe(HERE.parents[1]/'.cache/s6b/deps',
            'm=types.ModuleType("argon2");m.__file__="C:/outside/global.py";sys.modules["argon2"]=m;')
        self.assertFalse(value['result']['ready']);self.assertFalse(value['backendImported'])
    def test_pinned_local_module_paths_ready(self):
        value=self.probe(HERE.parents[1]/'.cache/s6b/deps')
        self.assertTrue(value['result']['ready']);self.assertTrue(value['result']['local_paths'])

if __name__=='__main__':unittest.main()
