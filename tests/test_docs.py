import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('docs', Path(__file__).resolve().parents[1] / 'scripts/docs.py')
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


class DocumentationTests(unittest.TestCase):
    def test_extracted_installation_links_and_anchors(self):
        files = {'README.md': b'[API](docs/API.md#calls) ![render](docs/example.svg)',
                 'docs/API.md': b'# API\n## Calls\n[Home](../README.md)', 'docs/example.svg': None}
        self.assertEqual(docs.check_links(files), [])

    def test_absent_archive_document_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing local target'):
            docs.require_links({'README.md': b'[API](docs/API.md)'})

    def test_missing_heading_rejected(self):
        self.assertTrue(docs.check_links({'README.md': b'# Intro\n[API](#missing)'}))

    def test_external_and_code_examples_are_not_local_links(self):
        files = {'README.md': b'[site](https://example.com)\n```text\n[placeholder](missing)\n```\n`[placeholder](missing)`'}
        self.assertEqual(docs.check_links(files), [])

    def test_escape_outside_distribution_rejected(self):
        self.assertTrue(docs.check_links({'README.md': b'[outside](../file.md)'}))


if __name__ == '__main__':
    unittest.main()
