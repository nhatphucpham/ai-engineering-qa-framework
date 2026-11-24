"""Changed input pins must stop before any external supervisor launch."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .common import Error, sha
from .fixed_executor import execute
from .fresh_fixture import source_intake
from .linux_input_guard import load_worker, install_held_reader


class InputAdmissionTests(unittest.TestCase):
    def test_final_linux_boundary_denies_late_consistent_input_replacement(self):
        worker = load_worker()
        held = {name: sha(b'approved') for name in worker.TRUSTED_INPUTS}
        late = {name: b'changed after Windows admission' for name in held}
        reported = {name: sha(raw) for name, raw in late.items()}
        with patch.object(worker, 'read_staging', return_value=(late, reported)), patch.object(worker, 'VF1Engine') as engine:
            install_held_reader(worker, held)
            result = worker.run_worker('/unused', 'freshRun', 'freshJob')
            self.assertEqual(result['status'], 'unresolved')
            self.assertEqual(result['error']['code'], 'E_HELD_INPUT_PINS')
            self.assertEqual(result['error']['stage'], 'validate-input')
            engine.assert_not_called()

    def test_changed_staged_content_denied_before_external_launch(self):
        inputs = source_intake(project_id='freshProject', task_id='freshTask', handoff_id='freshHandoff', run_id='freshRun')
        pins = inputs['manifest']['inputHashes']
        approved = Path(__file__).resolve().parents[1] / '.cache/s6/vf1'
        approved.mkdir(parents=True, exist_ok=True)
        for misreport in (False, True):
            with self.subTest(misreported_stage_hash=misreport), tempfile.TemporaryDirectory(dir=approved) as folder:
                self.assertTrue(Path(folder).resolve().is_relative_to(approved.resolve()))
                staging = Path(folder) / 'staging'
                def stage(target, run_id, job_id):
                    target.mkdir()
                    for name in pins:
                        file = target / name; file.parent.mkdir(parents=True, exist_ok=True)
                        file.write_bytes(b'changed after server registration')
                    return pins if misreport else {name: sha((target / name).read_bytes()) for name in pins}
                with patch('spikes.m50_worker.qa_executor.stage', stage), patch('spikes.m50_worker.qa_executor.wsl') as wsl, patch('subprocess.Popen') as launch:
                    with self.assertRaises(Error) as caught:
                        execute(Path(folder), staging, 'freshRun', 'freshJob', pins, lambda: None,
                                controller=None, worker_token=None, body={'run_id': 'freshRun'},
                                admission={'jobId': 'freshJob', 'manifest': {'inputHashes': pins}})
                    self.assertEqual(caught.exception.code, 'E_HELD_INPUT_PINS')
                    launch.assert_not_called(); wsl.assert_not_called()


if __name__ == '__main__':
    unittest.main()
