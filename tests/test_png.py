"""Ensure PNG error detection checks pixels and checksums, not only a signature."""
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check import inspect_png


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))


def png(pixels=b'\x00\xFF\x00\x00'):
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


class PngTests(unittest.TestCase):
    def inspect(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.png'
            path.write_bytes(data)
            return inspect_png(path)

    def test_valid_pixels(self):
        self.assertIsNone(self.inspect(png()))

    def test_truncated_file(self):
        self.assertIsNotNone(self.inspect(png()[:-5]))

    def test_bad_crc(self):
        data = bytearray(png()); data[-1] ^= 1
        self.assertIsNotNone(self.inspect(bytes(data)))

    def test_missing_pixels(self):
        self.assertIsNotNone(self.inspect(png(b'')))

    def test_bad_filter(self):
        self.assertIsNotNone(self.inspect(png(b'\x05\xFF\x00\x00')))

    def test_svg_error_disguised_as_png(self):
        self.assertIsNotNone(self.inspect(b'<svg>Error</svg>'))


if __name__ == '__main__':
    unittest.main()
