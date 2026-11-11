"""Independent prerequisite rejection checks. No DB connection or mock DB gate."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import local


class PreflightTests(unittest.TestCase):
    def test_absent_tools_are_not_ready_and_no_binary_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(local, 'CACHE', Path(folder)), patch.object(local, 'BIN', Path(folder) / 'bin'), \
                    patch.object(local, 'CONFIG', Path(folder) / 'cluster.json'), \
                    patch.object(local, 'command', side_effect=AssertionError('No binaries expected')):
                result = local.inventory()
                self.assertFalse(result['toolchainReady'])
                self.assertFalse(result['archiveIntegrity'])

    def test_bad_marker_rejected_before_process_or_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'cluster.json'
            marker.write_text(json.dumps({'kind': 'real-database', 'port': 5432}))
            with patch.object(local, 'CONFIG', marker), \
                    patch.object(local, 'command', side_effect=AssertionError('Must reject before status')):
                with self.assertRaises(ValueError):
                    local.read_config()

    def test_postgres_environment_cleared_without_echo(self):
        with patch.dict(local.os.environ, {'PGSERVICE': 'synthetic-not-contacted', 'PGPASSWORD': 'dummy'}, clear=True):
            local.clean_environment()
            self.assertFalse(any(key.upper().startswith('PG') for key in local.os.environ))

    def test_missing_or_mismatched_driver_metadata_rejected_without_import(self):
        with tempfile.TemporaryDirectory() as folder:
            deps = Path(folder)
            with patch.object(local.importlib, 'import_module', side_effect=AssertionError('No fallback import')):
                self.assertFalse(local.driver_inventory(deps)['ready'])
                for name in local.DRIVER_PINS:
                    metadata = deps / (name.replace('-', '_') + '-wrong.dist-info')
                    metadata.mkdir()
                    (metadata / 'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: 0.0.0\n')
                result = local.driver_inventory(deps)
                self.assertFalse(result['ready'])
                self.assertEqual(set(result['versions'].values()), {'0.0.0'})

    def test_setup_never_overwrites_existing_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'cluster.json'
            marker.write_text('existing')
            with patch.object(local, 'CONFIG', marker), patch.object(local, 'CACHE', Path(folder)), \
                    patch.object(local, 'command', side_effect=AssertionError('No initdb expected')):
                with self.assertRaises(ValueError):
                    local.setup()
            self.assertEqual(marker.read_text(), 'existing')

    def test_globally_loaded_driver_is_not_a_local_toolchain(self):
        with tempfile.TemporaryDirectory() as folder:
            deps = Path(folder) / 'deps'
            deps.mkdir()
            modules = []
            for name, version in local.DRIVER_PINS.items():
                metadata = deps / (name.replace('-', '_') + '-pin.dist-info')
                metadata.mkdir()
                (metadata / 'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n')
                modules.append(SimpleNamespace(__file__=str(Path(folder) / 'outside.py'),
                    __version__=version, pq=SimpleNamespace(__impl__='binary')))
            with patch.object(local.importlib, 'import_module', side_effect=modules):
                result = local.driver_inventory(deps)
            self.assertFalse(result['ready'])
            self.assertFalse(result['localModulePaths'])


if __name__ == '__main__':
    unittest.main()
