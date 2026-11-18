"""The pre-push byte policy must never authorize edits to historical fixture policy."""
import unittest
from spikes.vf1.verify import permitted_vf1_attributes


class GitBytePolicyTest(unittest.TestCase):
    def test_only_exact_new_vf1_paths_may_be_appended(self):
        original=b'/old.py -text\n'
        header=b'\n# Preserve exact reviewed VF1 source/evidence and pre-push records.\n'
        flags=b' -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n'
        self.assertTrue(permitted_vf1_attributes(original,original+header+b'/spikes/vf1/run_vf1.py'+flags))
        self.assertTrue(permitted_vf1_attributes(original,original+header+b'/docs/vf1-results/batch/checks.json'+flags))
        for path in (b'/examples/mock/fixture.py',b'/spikes/vf1/../../old.py',b'/spikes/vf1/*',b'/spikes/vf1/'):
            with self.subTest(path=path):
                self.assertFalse(permitted_vf1_attributes(original,original+header+path+flags))
        valid=original+header+b'/spikes/vf1/run_vf1.py'+flags
        self.assertFalse(permitted_vf1_attributes(original,valid.replace(b'/old.py',b'/other.py',1)))
        self.assertFalse(permitted_vf1_attributes(original,valid+b'/spikes/vf1/run_vf1.py'+flags))


if __name__=='__main__':unittest.main()
