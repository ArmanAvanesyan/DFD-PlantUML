"""Integrity checks for candidate archives; no Docker required."""
import importlib.util
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

spec = importlib.util.spec_from_file_location('distribution', Path(__file__).resolve().parents[1] / 'scripts/distribution.py')
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


class DistributionTests(unittest.TestCase):
    revision = 'a' * 40

    def setUp(self):
        self.files = {name: b'fixture\n' for name in distribution.FIXED}
        self.files['examples/example.puml'] = b'@startuml\n@enduml\n'

    def test_deterministic_and_complete(self):
        first = distribution.build_archive(self.files, self.revision)
        self.assertEqual(first, distribution.build_archive(dict(reversed(list(self.files.items()))), self.revision))
        self.assertEqual(distribution.verify_archive(first, self.revision), self.files)

    def test_development_archive_discloses_working_tree(self):
        data = distribution.build_archive(self.files, self.revision, 'working-tree')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest = json.loads(archive.read('dfd-plantuml/MANIFEST.json'))
        self.assertEqual(manifest['source_state'], 'working-tree')
        self.assertEqual(manifest['revision'], self.revision)

    def modified_archive(self, alter):
        original = distribution.build_archive(self.files, self.revision)
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output, 'w') as target:
            for item in source.infolist():
                name, data = alter(item.filename, source.read(item))
                item.filename = name
                target.writestr(item, data)
        return output.getvalue()

    def test_corrupt_payload_rejected(self):
        data = self.modified_archive(lambda name, data: (name, b'changed' if name.endswith('/DFD.puml') else data))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            distribution.verify_archive(data, self.revision)

    def test_traversal_rejected(self):
        data = self.modified_archive(lambda name, data: ('dfd-plantuml/../escape' if name.endswith('/DFD.puml') else name, data))
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            distribution.verify_archive(data, self.revision)

    def test_extra_member_rejected(self):
        data = self.modified_archive(lambda name, data: (name.replace('/DFD.puml', '/secret.txt'), data))
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            distribution.verify_archive(data, self.revision)

    def test_missing_required_file_rejected(self):
        del self.files['LICENSE']
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            distribution.verify_archive(distribution.build_archive(self.files, self.revision), self.revision)

    def test_duplicate_members_rejected(self):
        data = distribution.build_archive(self.files, self.revision)
        output = io.BytesIO(data)
        with zipfile.ZipFile(output, 'a') as archive:
            original = archive.getinfo('dfd-plantuml/DFD.puml')
            # zipfile warns about the deliberate adversarial duplicate.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                archive.writestr(original, b'duplicate')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            distribution.verify_archive(output.getvalue(), self.revision)

    def test_symlink_member_rejected(self):
        data = distribution.build_archive(self.files, self.revision)
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(output, 'w') as target:
            for item in source.infolist():
                content = source.read(item)
                if item.filename.endswith('/DFD.puml'):
                    item.external_attr = 0o120777 << 16
                target.writestr(item, content)
        with self.assertRaisesRegex(ValueError, 'member type'):
            distribution.verify_archive(output.getvalue(), self.revision)

    def test_wrong_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'revision mismatch'):
            distribution.verify_archive(distribution.build_archive(self.files, self.revision), 'b' * 40)

    def test_packaged_document_link_must_resolve_inside_archive(self):
        self.files['README.md'] = b'[API](docs/NOT-PACKAGED.md)'
        with self.assertRaisesRegex(ValueError, 'missing local target'):
            distribution.verify_archive(distribution.build_archive(self.files, self.revision), self.revision)


if __name__ == '__main__':
    unittest.main()
