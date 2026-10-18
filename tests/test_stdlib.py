"""Committed-source and adversarial-output tests for the stdlib preview exporter."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stdlib_export', ROOT / 'scripts/stdlib.py')
stdlib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stdlib)


class StdlibExportTests(unittest.TestCase):
    def test_encoder_rejects_raw_github_urls_even_in_comments(self):
        with self.assertRaisesRegex(ValueError, 'Raw GitHub URL'):
            stdlib.validate_includes('DFD.puml', b"' https://raw.githubusercontent.com/example/library.puml\n")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dfd-stdlib-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.output = Path(self.temp.name).resolve() / 'output'
        for name in stdlib.INPUTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        self.git('init', '-q')
        self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Committed fixture')
        return self.git('rev-parse', 'HEAD')

    def test_deterministic_allowlist_and_manifest(self):
        files = stdlib.build_export(self.root)
        self.assertEqual(files, stdlib.build_export(self.root))
        expected = {'dfd/' + n for n in stdlib.LIBRARIES}
        expected |= {f'dfd/_examples_/{n}.puml' for n in stdlib.EXAMPLES}
        self.assertEqual(set(files), expected | {'dfd/README.md', 'MANIFEST.json'})
        manifest = json.loads(files['MANIFEST.json'])
        self.assertEqual(manifest['source_commit'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(set(manifest['inputs']), set(stdlib.INPUTS))
        self.assertEqual(set(manifest['files']), set(files) - {'MANIFEST.json'})
        self.assertIn(b'version: unreleased\n', files['dfd/README.md'])
        self.assertNotIn(b'$DFD_ROOT', b''.join(files.values()))
        stdlib.write_export(files, self.output)
        stdlib.write_export(files, self.output)
        self.assertEqual(files, stdlib.check_export(self.root, 'HEAD', self.output))

    def test_working_tree_ignored_and_revision_respected(self):
        original = stdlib.build_export(self.root)
        old = self.git('rev-parse', 'HEAD')
        path = self.root / 'DFD.puml'
        path.write_bytes(path.read_bytes() + b"\n' future committed change\n")
        self.assertEqual(original, stdlib.build_export(self.root))
        self.commit()
        self.assertNotEqual(original, stdlib.build_export(self.root))
        self.assertEqual(original, stdlib.build_export(self.root, old))

    def test_only_approved_include_transformations(self):
        files = stdlib.build_export(self.root)
        for name in stdlib.LIBRARIES:
            source = (self.root / name).read_bytes()
            transformed = files['dfd/' + name]
            # Removing the license header leaves precisely the approved replacement.
            header_end = transformed.index(source.splitlines(keepends=True)[0])
            expected = source if name == 'DFD.puml' else source.replace(stdlib.ROUTING, b'!include <dfd/DFD>\n')
            self.assertEqual(transformed[header_end:], expected)
        for name in stdlib.EXAMPLES:
            self.assertIn(b'!include <dfd/DFD_Level_', files[f'dfd/_examples_/{name}.puml'])

    def test_changed_routing_rejected(self):
        path = self.root / 'DFD_Level_0.puml'
        path.write_bytes(path.read_bytes().replace(b'!include DFD.puml', b'!include different.puml'))
        self.commit()
        with self.assertRaisesRegex(ValueError, 'routing block'):
            stdlib.build_export(self.root)

    def test_network_or_local_dependency_rejected(self):
        for directive in (b'!includeurl https://example.invalid/file\n', b'!include ../other.puml\n', b'!includesub <other/lib>!part\n'):
            with self.subTest(directive=directive):
                path = self.root / 'DFD.puml'
                path.write_bytes((ROOT / 'DFD.puml').read_bytes() + directive)
                self.commit()
                with self.assertRaisesRegex(ValueError, 'include'):
                    stdlib.build_export(self.root)

    def test_missing_metadata_rejected(self):
        path = self.root / stdlib.TEMPLATE
        path.write_text(path.read_text().replace('license: MIT\n', ''))
        self.commit()
        with self.assertRaisesRegex(ValueError, 'metadata'):
            stdlib.build_export(self.root)

    def test_source_symlink_rejected(self):
        path = self.root / 'DFD.puml'
        path.unlink()
        path.symlink_to('DFD_Level_0.puml')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            stdlib.build_export(self.root)

    def test_extra_and_stale_outputs_rejected_without_deletion(self):
        files = stdlib.build_export(self.root)
        stdlib.write_export(files, self.output)
        extra = self.output / 'personal.txt'
        extra.write_text('preserve me')
        with self.assertRaisesRegex(ValueError, 'unexpected output'):
            stdlib.write_export(files, self.output)
        with self.assertRaisesRegex(ValueError, 'unexpected files'):
            stdlib.check_export(self.root, 'HEAD', self.output)
        self.assertEqual(extra.read_text(), 'preserve me')
        extra.unlink()
        target = self.output / 'dfd/DFD.puml'
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            stdlib.write_export(files, self.output)
        self.assertEqual(target.read_bytes(), b'changed')

    def test_output_symlink_and_unexpected_empty_directory_rejected(self):
        files = stdlib.build_export(self.root)
        self.output.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            stdlib.write_export(files, self.output)
        self.output.unlink()
        self.output.mkdir()
        (self.output / 'unrelated').mkdir()
        with self.assertRaisesRegex(ValueError, 'Unexpected output directory'):
            stdlib.write_export(files, self.output)

    def test_check_missing_output_does_not_create_it(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            stdlib.check_export(self.root, 'HEAD', self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
