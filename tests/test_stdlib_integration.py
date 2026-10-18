"""Integration gates must reject stale/mismatched resources and unsafe routing."""
import hashlib
import importlib.util
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('dfd_integration', SCRIPTS / 'stdlib_integration.py')
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)


class IntegrationGuards(unittest.TestCase):
    def test_bundle_routes_all_profiles_and_core_without_network(self):
        source = '@startdot\n!include ../../DFD_Level_0.puml\n!include ../../DFD.puml\n@enddot\n'
        self.assertEqual(integration.bundled(source), '@startdot\n!include <dfd/DFD_Level_0>\n!include <dfd/DFD>\n@enddot\n')

    def candidate(self, root, content=b'payload', namespace=b'dfd\n'):
        jar = root / 'candidate.jar'
        with zipfile.ZipFile(jar, 'w') as archive:
            archive.writestr('stdlib/dfd/puml.spm', content)
            archive.writestr('stdlib/home.spm', namespace)
        return jar

    def test_jar_resources_are_verified_by_bytes_not_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self.candidate(Path(tmp))
            expected = {'dfd/puml.spm': hashlib.sha256(b'payload').hexdigest()}
            integration.resources_in_jar(jar, expected)
            expected['dfd/puml.spm'] = hashlib.sha256(b'other').hexdigest()
            with self.assertRaisesRegex(ValueError, 'resource mismatch'):
                integration.resources_in_jar(jar, expected)

    def test_namespace_requires_exact_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self.candidate(Path(tmp), namespace=b'notdfd\n')
            with self.assertRaisesRegex(ValueError, 'namespace index'):
                integration.resources_in_jar(jar, {})

    def test_missing_candidate_resource_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self.candidate(Path(tmp))
            with self.assertRaises(KeyError):
                integration.resources_in_jar(jar, {'dfd/info.spm': 'missing'})

    def test_expected_graphviz_failure_accepts_raw_diagnostic_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'invalid.svg'
            path.write_text("Error: <stdin>: syntax error in line 5 near '!'\n")
            proc = SimpleNamespace(returncode=0)
            self.assertTrue(integration.rejection(proc, [path], 'syntax error', 'reject_graphviz'))
            path.write_text('source text mentions syntax error')
            self.assertFalse(integration.rejection(proc, [path], 'syntax error', 'reject_graphviz'))

    def test_dot_comparison_preserves_quoted_blank_lines_and_spacing(self):
        original = b'@startdot\n\n  graph [label="first\n\nsecond \\"quoted\\" line"];\n  \nnode [label="Unicode \xc3\xa9"];\n'
        expected = b'@startdot\n  graph [label="first\n\nsecond \\"quoted\\" line"];\nnode [label="Unicode \xc3\xa9"];\n'
        self.assertEqual(integration.canonical_dot(original), expected)
        self.assertNotEqual(integration.canonical_dot(b'label="a\n\nb";\n'), integration.canonical_dot(b'label="a\nb";\n'))

    def test_official_control_requires_missing_dfd_namespace_root_cause(self):
        self.assertTrue(integration.missing_namespace('java.io.FileNotFoundException: stdlib/dfd/info.spm (No such file or directory)'))
        self.assertFalse(integration.missing_namespace('Fatal parsing error'))
        self.assertFalse(integration.missing_namespace('FileNotFoundException: unrelated.puml'))

    def test_numbered_outputs_cannot_overwrite_another_fixture(self):
        cases = [{'name': 'multiple', 'output_count': 2}, {'name': 'multiple_001', 'output_count': 1}]
        with self.assertRaisesRegex(ValueError, 'artifact name'):
            integration.check_case_names(cases)

    def test_bundled_container_mounts_no_local_library_directory(self):
        cases = Path('/isolated/validation/cases/bundled')
        jar = Path('/isolated/validation/candidate.jar')
        command = integration.docker('sha256:pinned', {'platform': 'linux/amd64'}, cases,
                                     ['render.sh'], candidate=jar)
        mounts = [command[i + 1] for i, word in enumerate(command) if word == '-v']
        self.assertIn(str(cases) + ':/work', mounts)
        self.assertIn(str(jar) + ':/candidate.jar:ro', mounts)
        self.assertNotIn('/isolated/validation:/work', mounts)
        self.assertEqual(command[command.index('--network') + 1], 'none')

    def test_semantics_include_text_and_arrow_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'valid.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><g class="graph"><title>filename</title><g class="edge"><polygon fill="red"/><text>label</text></g></g></svg>')
            before = integration.semantic(path)
            path.write_text(path.read_text().replace('filename', 'another'))
            self.assertEqual(before, integration.semantic(path))
            path.write_text(path.read_text().replace('red', 'blue'))
            self.assertNotEqual(before, integration.semantic(path))


if __name__ == '__main__':
    unittest.main()
