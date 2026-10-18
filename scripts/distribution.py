#!/usr/bin/env python3
"""Build and verify a deterministic candidate archive; never tag or publish."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from docs import require_links

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'dfd-plantuml'
FIXED = ('DFD.puml', 'DFD_Level_0.puml', 'DFD_Level_1.puml', 'LICENSE',
         'README.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'docs/MIGRATION.md',
         'docs/RELEASING.md', 'docs/INSTALLATION.md', 'docs/API.md',
         'docs/COMPATIBILITY.md', 'docs/ARCHITECTURE.md', 'docs/STDLIB.md', 'docs/rendered/level_0.svg',
         'docs/rendered/level_1.svg', 'docs/rendered/customization.svg')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload(root):
    names = list(FIXED) + sorted(p.relative_to(root).as_posix() for p in (root / 'examples').glob('*.puml'))
    if not any(name.startswith('examples/') for name in names):
        raise ValueError('No executable examples found')
    return {name: (root / name).read_bytes() for name in names}


def build_archive(files, revision, source_state="committed"):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Revision must be a full lowercase commit SHA')
    manifest = {'revision': revision, 'source_state': source_state, 'files': {name: digest(data) for name, data in sorted(files.items())}}
    members = dict(files)
    members['MANIFEST.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    output = io.BytesIO()
    # Stored members avoid zlib-version-dependent compressed output.
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(f'{PREFIX}/{name}', date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def verify_archive(data, revision):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Duplicate archive members')
        members = {}
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or path.as_posix() != info.filename or not path.parts or path.parts[0] != PREFIX:
                raise ValueError('Unsafe archive path')
            if info.is_dir() or info.external_attr >> 16 != 0o100644:
                raise ValueError('Unexpected archive member type')
            name = path.relative_to(PREFIX).as_posix()
            allowed = name in FIXED or name == 'MANIFEST.json' or bool(re.fullmatch(r'examples/[^/]+\.puml', name))
            if not allowed:
                raise ValueError('Unexpected archive member: ' + name)
            members[name] = archive.read(info)
    manifest = json.loads(members.pop('MANIFEST.json'))
    if manifest.get('revision') != revision:
        raise ValueError('Manifest revision mismatch')
    if not set(FIXED).issubset(members) or not any(n.startswith('examples/') for n in members):
        raise ValueError('Incomplete distribution')
    if manifest.get('files') != {name: digest(content) for name, content in sorted(members.items())}:
        raise ValueError('Manifest checksum mismatch')
    require_links(members)
    return members


def check_render(files, toolchain, evidence):
    from toolchain import load, prepare
    from check import inspect_png
    lock = load(toolchain)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'toolchain.json').write_text(json.dumps(lock, indent=2) + '\n')
    results = []
    if not re.fullmatch(r'.+@sha256:[0-9a-f]{64}', lock['image']):
        raise ValueError('Docker toolchain must be digest-pinned')
    image = prepare(lock)
    with tempfile.TemporaryDirectory(prefix='dfd-distribution-') as directory:
        extracted = Path(directory)
        for name, content in files.items():
            dest = extracted / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        blocks = re.findall(r'```text\n(@start(?:uml|dot)\n.*?)```', files['README.md'].decode(), re.S)
        if len(blocks) != 1:
            raise ValueError('Expected one README installation example')
        installation = re.sub(r'^!\$DFD_ROOT = .*\n', '', blocks[0], flags=re.M).replace('!includeurl $DFD_ROOT/', '!include ')
        (extracted / 'installation.puml').write_text(installation)
        examples = sorted((extracted / 'examples').glob('*.puml')) + [extracted / 'installation.puml']
        for source in examples:
            relative = source.relative_to(extracted).as_posix()
            command = ['docker', 'run', '--rm', '--platform', lock['platform'], '--network', 'none',
                       '-e', 'PLANTUML_SECURITY_PROFILE=UNSECURE', '-v', f'{extracted}:/work',
                       '-v', f'{ROOT / "scripts"}:/harness:ro', '-w', '/work', '--entrypoint', 'sh',
                       image, '/harness/render.sh', '-charset', 'UTF-8', '-tsvg', relative]
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (evidence / (source.stem + '.svg.log')).write_text(result.stdout + result.stderr)
            rendered = source.with_suffix('.svg')
            if result.returncode or not rendered.is_file():
                raise ValueError(f'Archive render failed for {relative}: {result.stdout}{result.stderr}')
            svg = ET.parse(rendered).getroot()
            if svg.tag != '{http://www.w3.org/2000/svg}svg' or not any(g.get('class') == 'graph' for g in svg.findall('.//{http://www.w3.org/2000/svg}g')):
                raise ValueError(f'Archive contains an error diagram: {relative}')
            (evidence / rendered.name).write_bytes(rendered.read_bytes())
            command[-2] = '-tpng'
            png_result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (evidence / (source.stem + '.png.log')).write_text(png_result.stdout + png_result.stderr)
            png = source.with_suffix('.png')
            error = inspect_png(png)
            png_diagnostics = png_result.stdout + png_result.stderr
            if png_result.returncode or error or re.search(r'(?i)(exception|error|cannot|failed)', png_diagnostics):
                raise ValueError(f'Archive PNG render failed for {relative}: {error}; {png_result.stdout}{png_result.stderr}')
            (evidence / png.name).write_bytes(png.read_bytes())
            results.append({'example': relative, 'svg': rendered.name, 'png': png.name, 'passed': True})
            print('PASS offline archive render (SVG and PNG): ' + relative)
        (evidence / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', help='Full candidate commit SHA (default: git HEAD); archive uses current working tree files')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/dist')
    parser.add_argument('--check', action='store_true', help='Check reproducibility, contents, extraction and offline rendering')
    parser.add_argument('--allow-dirty', action='store_true', help='Development only: package modified/uncommitted files, marked working-tree in manifest')
    parser.add_argument('--toolchain', choices=['baseline', 'current'], default='baseline')
    args = parser.parse_args()
    revision = args.revision or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = payload(ROOT)
    source_state = 'committed'
    for name, content in files.items():
        original = subprocess.run(['git', 'show', f'{revision}:{name}'], cwd=ROOT, capture_output=True)
        if original.returncode or original.stdout != content:
            if not args.allow_dirty:
                raise ValueError(f'{name} differs from candidate revision; commit changes first or use --allow-dirty for development checks')
            source_state = 'working-tree'
    archive = build_archive(files, revision, source_state)
    verified = verify_archive(archive, revision)
    if args.check:
        if archive != build_archive(payload(ROOT), revision, source_state):
            raise ValueError('Archive is not reproducible')
        check_render(verified, args.toolchain, args.output / "render" / args.toolchain)
    args.output.mkdir(parents=True, exist_ok=True)
    name = f'{PREFIX}-{revision}.zip'
    (args.output / name).write_bytes(archive)
    (args.output / 'SHA256SUMS').write_text(f'{digest(archive)}  {name}\n')
    print(f'Candidate archive: {args.output / name}')
    print('SHA256: ' + digest(archive))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, ET.ParseError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
