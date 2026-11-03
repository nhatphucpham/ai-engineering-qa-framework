"""Run only the synthetic fixtures shipped here; no external dependencies."""

import difflib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
WORKER = """
import json
import sys
import unittest
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[1])
result = unittest.TestResult()
suite.run(result)
print(json.dumps({
    'tests': result.testsRun,
    'failures': [trace for _, trace in result.failures],
    'errors': [trace for _, trace in result.errors],
    'skipped': len(result.skipped),
}))
"""


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    mismatches = []
    for case in manifest["cases"]:
        folder = ROOT / case["directory"]
        before = (folder / "before.py").read_text()
        after = (folder / "after.py").read_text()
        expected_diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="before.py", tofile="after.py",
        ))
        if (folder / "change.diff").read_text() != expected_diff:
            mismatches.append(f"{case['id']}: diff does not match snapshots")
        evidence = json.loads((folder / "evidence.mock.json").read_text())
        print(f"\n{case['id']}: {case['purpose']}")
        print(f"  evidence snapshot={evidence['snapshot']}; head={case['head']}")
        for module, expected in case["checks"].items():
            try:
                completed = subprocess.run(
                    [sys.executable, "-B", "-c", WORKER, module],
                    cwd=folder, capture_output=True, text=True, timeout=10,
                    check=False,
                )
                if completed.returncode:
                    raise RuntimeError(completed.stderr)
                observed = json.loads(completed.stdout)
                counts = {
                    "tests": observed["tests"],
                    "failures": len(observed["failures"]),
                    "errors": len(observed["errors"]),
                    "skipped": observed["skipped"],
                }
                matched = counts == expected
                print(f"  {module}: {counts} — {'MATCH' if matched else 'MISMATCH'}")
                for trace in observed["failures"] + observed["errors"]:
                    print(trace.rstrip())
                if not matched:
                    mismatches.append(f"{case['id']}/{module}: expected {expected}")
            except (OSError, subprocess.TimeoutExpired, ValueError, RuntimeError) as error:
                mismatches.append(f"{case['id']}/{module}: {error}")
        print(f"  Expected review: {case['expected_review']}")
    if mismatches:
        print("\nFixture mismatches:")
        print("\n".join(mismatches))
        return 1
    print("\nAll synthetic fixtures match their declared outcomes.")
    print("Expected test failures demonstrate bugs; this is not a QA evaluator or approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
