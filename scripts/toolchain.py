"""Prepare pinned native SVG/PNG renderer images; rendering itself stays offline."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name='baseline'):
    filename = 'toolchain.json' if name == 'baseline' else 'toolchain-current.json'
    lock = json.loads((ROOT / 'scripts' / filename).read_text())
    if not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', lock['image']):
        raise ValueError('Renderer base must be digest-pinned')
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', lock['ubuntu_snapshot']):
        raise ValueError('Ubuntu snapshot must be dated')
    return lock


def prepare(lock):
    recipe = (ROOT / 'scripts/Dockerfile').read_bytes()
    fingerprint = hashlib.sha256(recipe + json.dumps(lock, sort_keys=True).encode()).hexdigest()
    tag = 'dfd-plantuml-renderer:' + fingerprint
    found = subprocess.run(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True, capture_output=True)
    if found.returncode:
        print('Preparing pinned SVG/PNG toolchain: ' + lock['plantuml'], file=sys.stderr, flush=True)
        subprocess.run(['docker', 'build', '--platform', lock['platform'], '--build-arg', 'BASE_IMAGE=' + lock['image'],
                        '--build-arg', 'UBUNTU_SNAPSHOT=' + lock['ubuntu_snapshot'], '-f', str(ROOT / 'scripts/Dockerfile'),
                        '-t', tag, str(ROOT / 'scripts')], check=True, stdout=sys.stderr)
        found = subprocess.run(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True, capture_output=True, check=True)
    image = found.stdout.strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('Invalid prepared image content ID')
    return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain', choices=['baseline', 'current'], default='baseline')
    args = parser.parse_args()
    print(prepare(load(args.toolchain)))
