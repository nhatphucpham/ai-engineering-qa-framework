"""Controller-bound original VF1 execution and private source staging."""
from contextlib import closing, contextmanager
import re
import shutil
import subprocess
import time

from runtime_candidate.common import Error, canonical, require, sha
from runtime_candidate.storage import Denied, psycopg
from spikes.s4f.unit import ROOT, wsl
from spikes.vf1.run_vf1 import stage

from .profile_unit import ProfileUnit


class ExecutionInterrupted(RuntimeError):
    """Normal QA stopped. An optional owned cleanup pair goes to the enrolled collector."""
    def __init__(self, code, *, recovery=None, pair=None, proof=None, reconciliation_error=None):
        super().__init__(code)
        self.code = code
        self.recovery = recovery
        self.pair = pair
        self.proof = proof
        self.reconciliation_error = reconciliation_error


def _code(exc):
    code = getattr(exc, 'code', str(exc))
    return code if isinstance(code, str) and re.fullmatch(r'E_[A-Z_]{1,45}', code) else 'E_UNRESOLVED'


def _recover(controller, body, worker_token, original, output, cause):
    recovery = None
    try:
        resource, prior = controller.rebuild(body['project'], body['run_id'])
        require(prior is None and original.name == resource.anchor['context']['unit'], 'E_STALE')
        try:
            recovery, loss = controller.fence(resource, original, worker_token)
        except Error as exc:
            if exc.code != 'E_AUTHORITY':
                raise
            # With live authority, confirm a real loss by stopping only the exact owned unit.
            original.kill_original()
            recovery, loss = controller.fence(resource, original, worker_token)
        if original.process.poll() is None:
            original.kill_original()
        original_absent = original.close()
        with closing(ProfileUnit('replacement', output, resource.anchor)) as replacement:
            recovery = controller.attach(recovery, replacement)
            pair, observed = controller.cleanup(recovery, replacement)
        proof = dict(observed, originalUnit=original.name, originalProcess=original.ready['process'],
                     originalAbsence=original_absent, loss=loss, replacementUnit=replacement.name,
                     replacementProcess=replacement.ready['process'], replacementAbsence=replacement.absence())
        return ExecutionInterrupted(_code(cause), recovery=recovery, pair=pair, proof=proof)
    except (Error, Denied, RuntimeError, OSError, KeyError, subprocess.SubprocessError, psycopg.Error) as exc:
        return ExecutionInterrupted(_code(cause), recovery=recovery, reconciliation_error=_code(exc))


@contextmanager
def qa_original(output, staging, run_id, job_id, held_input_hashes, check_authority=None):
    staging_root = ROOT / '.cache/s6/vf1'
    require(staging != staging_root and staging.is_relative_to(staging_root)
            and '..' not in staging.parts, 'E_INPUT_SCOPE')
    pins = stage(staging, run_id, job_id)
    require(pins == held_input_hashes and all(sha((staging / name).read_bytes()) == value
            for name, value in pins.items()), 'E_HELD_INPUT_PINS')
    mapped = wsl('wslpath', '-a', staging.as_posix())
    require(mapped.returncode == 0 and mapped.stdout.startswith('/mnt/'), 'E_WSLCONFIG')
    init = {'staging': mapped.stdout.strip(), 'runId': run_id, 'jobId': job_id, 'inputHashes': held_input_hashes}
    unit = ProfileUnit('original', output, init, check_authority=check_authority)
    try:
        yield unit
    finally:
        unit.close()


def execute_qa(output, staging, run_id, job_id, held_input_hashes, check_authority, *,
               controller, worker_token, body, admission, after_live=None):
    require((run_id, job_id, held_input_hashes) ==
            (body['run_id'], admission['jobId'], admission['manifest']['inputHashes']), 'E_BINDING')
    with qa_original(output, staging, run_id, job_id, held_input_hashes, check_authority) as original:
        try:
            armed = controller.arm(worker_token, body, admission, original)
            resource = controller.fire(worker_token, body, admission, original, armed)
            if after_live is not None:
                after_live(original, resource)
            check_authority()
            release_pin = controller.release_qa(worker_token, body, admission, original, resource)
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                check_authority()
                live = original.request('poll', binding=resource.binding, journalPin=resource.pin, releasePin=release_pin)
                if live['running'] is False:
                    require(live['pid'] == 0, 'E_NOT_STOPPED')
                    break
                require(live['running'] is True and live['pid'] == resource.observed['initPid'], 'E_PROCESS')
                time.sleep(.1)
            else:
                require(False, 'E_TIMEOUT')
            record, normal_cleanup = controller.complete_qa(worker_token, body, admission, original, resource, release_pin)
        except (Error, Denied, RuntimeError, OSError, subprocess.SubprocessError, psycopg.Error) as exc:
            raise _recover(controller, body, worker_token, original, output, exc) from exc
    supervisor = dict(original.absence(), workerExitCode=original.process.returncode, **normal_cleanup)
    require(supervisor['workerExitCode'] == 0 and all(sha((staging / name).read_bytes()) == value
            for name, value in held_input_hashes.items()), 'E_INTEGRITY')
    with open(original.output_log.name, 'rb') as source, (output / 'worker.stdout.json').open('xb') as destination:
        shutil.copyfileobj(source, destination)
    with (output / 'supervisor.json').open('xb') as stream:
        stream.write(canonical(supervisor))
    return record, supervisor
