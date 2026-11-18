"""Boundary regressions; modified inputs here are authored test mutations, not live runs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from spikes.vf1 import run_vf1 as run


class OrchestrationTest(unittest.TestCase):
    def test_original_change_after_stage_cannot_relabel_executed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            case=base/'original'
            shutil.copytree(run.CASE,case)
            original=(case/'head/api.py').read_bytes()
            with patch.object(run,'CASE',case):
                hashes=run.stage(base/'staged','run-a','job-a')
                (case/'head/api.py').write_bytes(b'# newer unrelated source\n')
                record={'runId':'run-a','jobId':'job-a','finishedAt':'2026-11-18T00:00:00+00:00',
                        'inputHashes':hashes,'execution':{'observations':[]}}
                job=run.build_job(record,'a'*64,[],run.staged_payloads(base/'staged',hashes))
            offered=next(item for item in job['artifacts'] if item['relativePath']=='head/api.py')
            self.assertEqual(offered['text'].encode('utf-8'),original)
            self.assertEqual(offered['sha256'],hashes['case/head/api.py'])
            (base/'staged/case/head/api.py').write_bytes(b'# tampered stage\n')
            with self.assertRaisesRegex(RuntimeError,'Staged bytes'):
                run.staged_payloads(base/'staged',hashes)

    def test_self_consistent_job_tampering_cannot_replace_worker_pins(self):
        source=run.ROOT/'docs/vf1-results/vf1-20261118-r1/a'
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for name in ('execution.json','worker.stdout.json'):
                shutil.copyfile(source/name,folder/name)
            original=json.loads((source/'host-request.json').read_bytes())
            original_anchors=json.loads((source/'anchors.json').read_bytes())
            for mutation in ('text','outcome','observedAt','runId'):
                with self.subTest(mutation=mutation):
                    job,anchors=deepcopy(original),deepcopy(original_anchors)
                    if mutation=='text':
                        job['artifacts'][1]['text']+='# authored tamper\n'
                        job['artifacts'][1]['sha256']=hashlib.sha256(job['artifacts'][1]['text'].encode()).hexdigest()
                    elif mutation=='outcome':
                        job['observations'][0].update(outcome='error',reason='Authored mutation')
                    elif mutation=='observedAt':job['observedAt']='2026-11-18T00:00:00Z'
                    else:job['runId']=anchors['runId']='run-other'
                    data=run.canonical(job)
                    (folder/'host-request.json').write_bytes(data)
                    anchors['jobDigest']=hashlib.sha256(data).hexdigest()
                    with self.assertRaises(RuntimeError):
                        run.validate_execution_binding(folder,'a',job,anchors)

    def test_concurrent_output_creation_never_bypasses_exclusive_write(self):
        original_open=Path.open
        for resume,concurrent,accepted in [(False,b'expected',False),(True,b'other',False),(True,b'expected',True)]:
            with self.subTest(resume=resume,concurrent=concurrent),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'report.json'
                def racing_open(target,mode='r',*args,**kwargs):
                    if target==path and mode=='xb':
                        with original_open(target,'xb') as stream:stream.write(concurrent)
                    return original_open(target,mode,*args,**kwargs)
                with patch.object(Path,'open',racing_open):
                    if accepted:run.write_derived_bytes([(path,b'expected')],resume_exact=resume)
                    else:
                        with self.assertRaisesRegex(RuntimeError,'Concurrent output'):
                            run.write_derived_bytes([(path,b'expected')],resume_exact=resume)
                self.assertEqual(path.read_bytes(),concurrent)


if __name__=='__main__':unittest.main()
