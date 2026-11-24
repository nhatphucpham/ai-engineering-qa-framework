"""Source registration must not import the prior execution/reasoning answers."""
import unittest
from .fresh_fixture import source_intake


class SourceIntakeTest(unittest.TestCase):
    def test_fresh_intake_has_eight_byte_pinned_sources_and_no_observations(self):
        result = source_intake(project_id='freshProject', task_id='freshTask', handoff_id='freshHandoff', run_id='freshRun')
        bundle = result['bundle']
        self.assertEqual(len(result['sources']), 8)
        self.assertEqual(len(result['manifest']['inputHashes']), 9)
        self.assertEqual(bundle['evidence'], [])
        self.assertEqual(bundle['runs'][0]['state'], 'queued')
        self.assertIsNone(bundle['runs'][0]['lease'])
        self.assertEqual(bundle['runs'][0]['attempt'], 0)
        self.assertEqual(bundle['runs'][0]['projectConfigVersion'], 2)
        self.assertNotIn('assessment', result)
        self.assertEqual({row['id'] for row in bundle['artifacts']}, set(result['sources']))


if __name__ == '__main__':
    unittest.main()
