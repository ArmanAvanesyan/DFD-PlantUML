"""Contract tests for the extracted compatibility fixture inventory."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check import load_cases


class FixtureTests(unittest.TestCase):
    def test_inventory_and_engine_contract(self):
        baseline = {case['name']: case for case in load_cases()}
        current = {case['name']: case for case in load_cases('current')}
        self.assertEqual(len(baseline), 21)
        self.assertEqual(set(baseline), set(current))
        self.assertEqual(sum(case['expected_diagnostic'] is not None for case in baseline.values()), 7)
        self.assertIsNone(baseline['legacy_uml']['expected_diagnostic'])
        self.assertEqual(current['legacy_uml']['expected_diagnostic'], 'Syntax Error')
        self.assertEqual(baseline['multiple']['output_count'], 2)
        self.assertEqual(baseline['multiple']['source'].count('@startdot'), 2)
        self.assertEqual(baseline['reject_substring']['expected_diagnostic'], 'Unknown flow source: P1')
        self.assertIn('!include ../../DFD_Level_0.puml', baseline['empty_title']['source'])

    def temporary_manifest(self, entries):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'cases': entries}))
        return root

    def entry(self, **overrides):
        return dict(name='example', path='example.puml', expected_diagnostic=None,
                    output_count=1, **overrides)

    def test_missing_source_is_reported(self):
        root = self.temporary_manifest([self.entry()])
        with self.assertRaises(FileNotFoundError):
            load_cases(fixture_root=root)

    def test_duplicate_artifact_names_are_rejected(self):
        entry = self.entry()
        root = self.temporary_manifest([entry, entry])
        (root / 'example.puml').write_text('@startdot\n@enddot\n')
        with self.assertRaisesRegex(ValueError, 'duplicate fixture name'):
            load_cases(fixture_root=root)

    def test_path_cannot_escape_fixture_directory(self):
        entry = self.entry()
        entry['path'] = '../outside.puml'
        root = self.temporary_manifest([entry])
        with self.assertRaisesRegex(ValueError, 'inside fixture directory'):
            load_cases(fixture_root=root)

    def test_unknown_toolchain_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown fixture toolchain'):
            load_cases('future')


if __name__ == '__main__':
    unittest.main()
