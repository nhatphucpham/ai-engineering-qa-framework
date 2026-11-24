"""Final held-input boundary for the unchanged fixed Linux VF1 worker."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def install_held_reader(worker, expected):
    worker.require(isinstance(expected, dict) and set(expected) == set(worker.TRUSTED_INPUTS)
                   and all(isinstance(v, str) and worker.SHA256.fullmatch(v) for v in expected.values()), 'E_HELD_INPUT_PINS')
    held = dict(expected)
    original = worker.read_staging
    def read(path, run_id, job_id):
        payloads, reported = original(path, run_id, job_id)
        worker.require(reported == held and set(payloads) == set(held) and
                       all(hashlib.sha256(raw).hexdigest() == held[name] for name, raw in payloads.items()), 'E_HELD_INPUT_PINS')
        return payloads, reported
    worker.read_staging = read


def load_worker():
    path = ROOT / 'spikes/vf1/linux_worker.py'
    spec = importlib.util.spec_from_file_location('_m50_fixed_vf1_worker', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


def main():
    if len(sys.argv) != 5:
        return 2
    worker = load_worker()
    expected = json.loads(base64.b64decode(sys.argv.pop(), validate=True))
    install_held_reader(worker, expected)
    # The original worker collects immutable private payload bytes, invokes this
    # held-pin comparison before creating its engine, then stages only those bytes.
    return worker.main()


if __name__ == '__main__':
    raise SystemExit(main())
