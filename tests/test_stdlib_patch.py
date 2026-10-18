"""Exercise a real local patch against an isolated upstream Git checkout."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('stdlib_patch', ROOT / 'scripts/stdlib_patch.py')
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


class ContributionPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dfd-patch-tests-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.upstream = self.base / 'upstream'
        self.repo = self.base / 'source'
        self.output = self.base / 'review'
        for root in (self.repo, self.upstream):
            root.mkdir()
            patcher.git(root, 'init', '-q')
        (self.upstream / 'README.md').write_text(
            '# Stdlib\n\n  - [Domain Story library (DomainStory-PlantUML) [DomainStory]](#domain)\n\n'
            '## Domain Story library (DomainStory-PlantUML) [DomainStory]\n\nExisting text.\n')
        self.commit(self.upstream)
        base = patcher.git(self.upstream, 'rev-parse', 'HEAD').decode().strip()
        for name in patcher.build_export.__globals__['INPUTS']:
            dest = self.repo / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts/stdlib-lock.json').write_text(json.dumps({'stdlib': {'revision': base}}))
        self.commit(self.repo)

    def commit(self, root):
        patcher.git(root, 'add', '.')
        patcher.git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Fixture')

    def test_patch_is_deterministic_applies_and_has_only_catalog_and_payload(self):
        result = patcher.prepare(self.repo, 'HEAD', self.upstream, self.output)
        second = self.base / 'second'
        self.assertEqual(result, patcher.prepare(self.repo, 'HEAD', self.upstream, second))
        data = (self.output / 'contribution.patch').read_bytes()
        self.assertEqual(data, (second / 'contribution.patch').read_bytes())
        self.assertEqual(patcher.git(self.upstream, 'status', '--porcelain'), b'')
        patcher.git(self.upstream, 'apply', str(self.output / 'contribution.patch'))
        self.assertIn('## DFD-PlantUML [dfd]', (self.upstream / 'README.md').read_text())
        expected = {'README.md', 'stdlib/dfd/README.md', 'stdlib/dfd/DFD.puml',
                    'stdlib/dfd/DFD_Level_0.puml', 'stdlib/dfd/DFD_Level_1.puml',
                    *(f'stdlib/dfd/_examples_/{n}.puml' for n in ('level_0', 'level_1', 'customization'))}
        self.assertEqual(set(result['files']), expected)
        self.assertEqual({p.relative_to(self.upstream).as_posix() for p in (self.upstream / 'stdlib').rglob('*') if p.is_file()}, expected - {'README.md'})
        self.assertIn('version: unreleased', (self.upstream / 'stdlib/dfd/README.md').read_text())

    def test_refuses_dirty_or_wrong_upstream_and_stale_review(self):
        (self.upstream / 'unexpected').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'clean'):
            patcher.prepare(self.repo, 'HEAD', self.upstream, self.output)
        self.commit(self.upstream)
        with self.assertRaisesRegex(ValueError, 'locked'):
            patcher.prepare(self.repo, 'HEAD', self.upstream, self.output)
        self.output.mkdir()
        (self.output / 'keep').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'empty'):
            patcher.prepare(self.repo, 'HEAD', self.upstream, self.output)
        self.assertEqual((self.output / 'keep').read_text(), 'keep')

    def test_changed_catalog_is_not_silently_repaired(self):
        with self.assertRaisesRegex(ValueError, 'catalog'):
            patcher.catalog('# New layout\n')

    def test_explicit_metadata_is_committed_and_not_exported_as_payload(self):
        path = self.repo / 'packaging/stdlib/selected.json'
        path.write_text('{"version":"2.3.4"}')
        self.commit(self.repo)
        path.write_text('{"version":"9.9.9"}')
        result = patcher.prepare(self.repo, 'HEAD', self.upstream, self.output, 'packaging/stdlib/selected.json')
        self.assertEqual(result['export_manifest']['metadata']['version'], '2.3.4')
        patcher.git(self.upstream, 'apply', str(self.output / 'contribution.patch'))
        self.assertIn('version: 2.3.4', (self.upstream / 'stdlib/dfd/README.md').read_text())
        self.assertFalse((self.upstream / 'stdlib/dfd/selected.json').exists())

    def test_output_cannot_modify_upstream_or_follow_symlink(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            patcher.prepare(self.repo, 'HEAD', self.upstream, self.upstream / 'review')
        link = self.base / 'link'
        link.symlink_to(self.base / 'target')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            patcher.prepare(self.repo, 'HEAD', self.upstream, link)


if __name__ == '__main__':
    unittest.main()
