#!/usr/bin/env python3
"""Render compatibility fixtures in the digest-pinned toolchain; stdlib only."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import struct
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

from toolchain import load, prepare

ROOT = Path(__file__).resolve().parents[1]
LOCK = load()
IMAGE = None
OUTPUT = None


def docker(args, online=False, entrypoint=None):
    mount = OUTPUT if online else ROOT
    command = ['docker', 'run', '--rm', '--platform', LOCK['platform'],
               '--network', 'bridge' if online else 'none',
               '-e', 'PLANTUML_SECURITY_PROFILE=UNSECURE',
               '-v', f'{mount}:/work', '-w', '/work']
    if online:
        command += ['-v', f'{ROOT / "scripts"}:/harness:ro']
    command += ['--entrypoint', entrypoint or 'sh']
    if not entrypoint:
        args = ['/harness/render.sh' if online else '/work/scripts/render.sh'] + args
    return subprocess.run(command + [IMAGE] + args, text=True, capture_output=True, timeout=90)


def inspect_svg(path):
    try:
        root = ET.parse(path).getroot()
        if root.tag != '{http://www.w3.org/2000/svg}svg':
            return 'not an SVG document'
        text = ' '.join(root.itertext())
        if not any(g.get('class') == 'graph' for g in root.findall('.//{http://www.w3.org/2000/svg}g')):
            return 'error diagram: ' + text[:600]
        return None
    except (OSError, ET.ParseError) as exc:
        return str(exc)



def inspect_png(path):
    """Reject truncated/corrupt PNGs, including bad chunks and compressed pixels."""
    try:
        data = path.read_bytes()
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'not a PNG document'
        offset, chunks, pixels = 8, [], bytearray()
        width = height = depth = color = interlace = 0
        while offset < len(data):
            if offset + 12 > len(data):
                return 'truncated PNG chunk'
            length = struct.unpack('>I', data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            end = offset + 12 + length
            if end > len(data):
                return 'truncated PNG payload'
            payload = data[offset + 8:offset + 8 + length]
            crc = struct.unpack('>I', data[end - 4:end])[0]
            if zlib.crc32(kind + payload) != crc:
                return 'PNG checksum mismatch'
            chunks.append(kind)
            if kind == b'IHDR':
                if len(chunks) != 1 or length != 13:
                    return 'invalid PNG header'
                width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
                if not width or not height or width * height > 50000000 or compression or filtering or interlace:
                    return 'unsupported PNG dimensions/encoding'
            elif kind == b'IDAT':
                pixels.extend(payload)
            elif kind == b'IEND':
                if length or end != len(data):
                    return 'invalid PNG ending'
            offset = end
        if chunks[:1] != [b'IHDR'] or chunks[-1:] != [b'IEND'] or b'IDAT' not in chunks:
            return 'missing PNG chunks'
        allowed = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
        if depth not in allowed.get(color, ()) or (color == 3 and b'PLTE' not in chunks):
            return 'unsupported PNG color encoding'
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        row = (width * channels * depth + 7) // 8 + 1
        expected = row * height
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(pixels, expected + 1)
        if len(decoded) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            return 'invalid PNG pixel data'
        if any(decoded[start] > 4 for start in range(0, expected, row)):
            return 'invalid PNG scanline filter'
        return None
    except (OSError, ValueError, struct.error, zlib.error) as exc:
        return str(exc)


def load_cases(toolchain='baseline', fixture_root=None):
    """Load immutable source fixtures; paths are relative to build/<suite>/.

    Consumers may adapt include routing for bundled installation. Diagnostic
    expectations are engine-specific only where the engine changed its contract.
    """
    if toolchain not in ('baseline', 'current'):
        raise ValueError('Unknown fixture toolchain: ' + toolchain)
    directory = Path(fixture_root) if fixture_root is not None else ROOT / 'tests' / 'fixtures'
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported fixture manifest schema')
    cases, names = [], set()
    for entry in manifest['cases']:
        name = entry['name']
        if not re.fullmatch(r'[a-z][a-z0-9_]*', name) or name in names:
            raise ValueError('Invalid or duplicate fixture name: ' + name)
        names.add(name)
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Fixture path must stay inside fixture directory')
        expected = entry['expected_diagnostic']
        if isinstance(expected, dict):
            expected = expected[toolchain]
        if expected is not None and (not isinstance(expected, str) or not expected):
            raise ValueError('Expected diagnostic must be nonempty or null')
        count = entry['output_count']
        if type(count) is not int or count < 1:
            raise ValueError('Output count must be a positive integer')
        source = (directory / relative).read_text()
        cases.append(dict(name=name, source=source, expected_diagnostic=expected, output_count=count))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--toolchain', choices=['baseline', 'current'], default='baseline')
    parser.add_argument('--remote-ref', help='40-character commit in the official repository')
    args = parser.parse_args()
    if args.remote_ref and not re.fullmatch('[0-9a-f]{40}', args.remote_ref):
        parser.error('--remote-ref must be a full lowercase commit SHA')
    global LOCK, IMAGE, OUTPUT
    LOCK = load(args.toolchain)
    IMAGE = prepare(LOCK)
    out = ROOT / 'build' / (('remote-' if args.remote_ref else 'checks-') + args.toolchain)
    OUTPUT = out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    versions = docker(['-c', 'java -version; dot -V; dpkg-query -W libgd3; java -jar /opt/plantuml.jar -version'], entrypoint='sh')
    (out / 'toolchain.log').write_text(versions.stdout + versions.stderr)
    if versions.returncode:
        sys.exit(versions.stderr)
    cases = []
    for source in sorted((ROOT / 'examples').glob('*.puml')):
        dest = out / source.name
        dest.write_text(source.read_text().replace('../DFD_', '../../DFD_'))
        cases.append((dest, None))
    installation = re.findall(r"```text\n(@startdot\n.*?)```", (ROOT / 'README.md').read_text(), re.S)
    if len(installation) != 1:
        sys.exit('Expected exactly one documented remote installation example')
    path = out / 'installation.puml'
    path.write_text(re.sub(r'^!\$DFD_ROOT = .*\n', '', installation[0], flags=re.M).replace('!includeurl $DFD_ROOT/', '!include ../../'))
    cases.append((path, None))
    if not args.remote_ref:
        for case in load_cases(args.toolchain):
            path = out / (case['name'] + '.puml')
            path.write_text(case['source'])
            cases.append((path, case['expected_diagnostic']))

    else:
        prefix = f'https://raw.githubusercontent.com/ArmanAvanesyan/DFD-PlantUML/{args.remote_ref}/'
        for path, _ in cases:
            path.write_text(path.read_text().replace('@startdot\n', '@startdot\n!$DFD_ROOT = ' + json.dumps(prefix.rstrip('/')) + '\n').replace('!include ../../', '!includeurl $DFD_ROOT/'))
    readme_blocks = re.findall(r"```plantuml\n(.*?)```", (ROOT / 'README.md').read_text(), re.S)
    example_blocks = [p.read_text() for p in sorted((ROOT / 'examples').glob('*.puml'))]
    if sorted(readme_blocks) != sorted(example_blocks):
        sys.exit('README examples differ from executable examples')
    (out / 'runtime.json').write_text(json.dumps(dict(LOCK, prepared_image=IMAGE), indent=2) + '\n')
    results = []
    names = [path.stem for path, _ in cases]
    if len(names) != len(set(names)):
        sys.exit('Fixture and example names must be unique')
    output_counts = {case['name']: case['output_count'] for case in load_cases(args.toolchain)}
    for path, expected in cases:
        rel = path.name if args.remote_ref else path.relative_to(ROOT).as_posix()
        proc = docker(['-charset', 'UTF-8', '-tsvg', rel], online=bool(args.remote_ref))
        (path.with_suffix('.log')).write_text(proc.stdout + proc.stderr)
        svgs = sorted(p for p in out.glob(path.stem + '*.svg') if re.fullmatch(re.escape(path.stem) + r'(?:_[0-9]+)?', p.stem))
        if expected:
            diagnostics = proc.stdout + proc.stderr
            messages = []
            for svg in svgs:
                try:
                    root = ET.parse(svg).getroot()
                    texts = [''.join(e.itertext()) for e in root.findall('.//{http://www.w3.org/2000/svg}text')]
                    messages += texts[-1:]
                except ET.ParseError:
                    messages.append(svg.read_text(errors='replace'))
            # Match the rendered final diagnostic, never a source-code dump that
            # can quote an assertion which the renderer did not actually reach.
            if path.stem == 'reject_graphviz':
                matched = any('syntax error' in m.lower() and 'error:' in m.lower() for m in messages)
            elif path.stem == 'legacy_uml':
                matched = any('Syntax Error' in m or 'Please use @startdot' in m for m in messages)
            else:
                matched = any('Assertion error' in m and expected in m for m in messages)
            ok = matched and (proc.returncode != 0 or any(inspect_svg(p) for p in svgs))
            detail = 'expected rejection' if ok else str(messages) + diagnostics[:700]
        else:
            failures = [inspect_svg(p) for p in svgs]
            ok = proc.returncode == 0 and len(svgs) == output_counts.get(path.stem, 1) and not any(failures)
            detail = str(failures) + proc.stderr if not ok else 'valid SVG'
            if ok:
                pre = docker(['-charset', 'UTF-8', '-preproc', rel], online=bool(args.remote_ref))
                ok = pre.returncode == 0
                dot = path.with_suffix('.preproc').read_text()
                if path.stem == 'flow_directions':
                    ok = ok and all(token in dot for token in ['dir=forward', 'dir=back', 'dir=both'])
                if path.stem == 'optional_ids':
                    ok = ok and 'E1 | User' in dot and '<f0>D2' in dot
                if path.stem == 'styles':
                    ok = ok and all(token in dot for token in ['fillcolor="#ABCDEF"', 'color="#123456"', 'width=3 height=2']) and dot.count('style="dashed" color="#AA0000" penwidth=3') == 3
                if path.stem == 'customization':
                    ok = ok and all(token in dot for token in ['rankdir=TB', 'width=2.5 height=1.2', 'COLOR="#234567"', 'COLOR="#345678"'])
                if path.stem == 'special_labels':
                    rendered = ' '.join(ET.parse(svgs[0]).getroot().itertext())
                    ok = ok and all(token in rendered for token in ['Quotes "yes"', '& <tags> {x|y}', 'café', 'Հայերեն', 'first', 'second'])
                if path.stem in ('legacy_newlines', 'literal_newlines'):
                    texts = [e.text for e in ET.parse(svgs[0]).getroot().findall('.//{http://www.w3.org/2000/svg}text')]
                    if path.stem == 'legacy_newlines':
                        ok = ok and all(x in texts for x in ['Title', 'second', 'External', 'Boundary', 'Process', 'Store', 'Flow']) and not any('\\n' in (x or '') for x in texts)
                    else:
                        ok = ok and all(x in texts for x in [r'Title\nsecond', r'C:\new', r'Process\nsecond', r'Flow\nsecond'])
                if path.stem == 'backslash_paths':
                    texts = [e.text for e in ET.parse(svgs[0]).getroot().findall('.//{http://www.w3.org/2000/svg}text')]
                    ok = ok and all(x in texts for x in [r'\\server\share', r'path\\tail', 'end\\\\', 'one\\'])
                if path.stem == 'backslash':
                    ok = ok and 'C:\\temp' in ' '.join(ET.parse(svgs[0]).getroot().itertext())
                if not ok:
                    detail = 'preprocessor/output behavior assertion failed'
        results.append({'case': path.stem, 'passed': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + path.stem + ('' if ok else ': ' + detail))
    for name in ['level_0', 'level_1', 'customization', 'installation']:
        source = out / (name + '.puml')
        rel = source.name if args.remote_ref else source.relative_to(ROOT).as_posix()
        proc = docker(['-charset', 'UTF-8', '-tpng', rel], online=bool(args.remote_ref))
        (out / (name + '.png.log')).write_text(proc.stdout + proc.stderr)
        issue = inspect_png(source.with_suffix('.png'))
        ok = proc.returncode == 0 and issue is None and not re.search(r'Exception|Error:|Some diagram description contains errors', proc.stderr)
        results.append({'case': name + '_png', 'passed': bool(ok), 'detail': issue or proc.stderr or 'valid native PNG'})
        print(('PASS ' if ok else 'FAIL ') + name + '_png')
    # Verify that the detector rejects both error SVGs and non-XML Graphviz diagnostics.
    if not args.remote_ref:
        for name, content in [('bad_xml', 'Error: syntax error'), ('error_svg', '<svg xmlns="http://www.w3.org/2000/svg"><g><text>Syntax Error?</text></g></svg>')]:
            bad = out / (name + '.svg')
            bad.write_text(content)
            results.append({'case': 'detector_' + name, 'passed': bool(inspect_svg(bad)), 'detail': 'error artifact rejected'})
    artifacts = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(out.iterdir()) if path.is_file()}
    (out / 'artifacts.json').write_text(json.dumps(artifacts, indent=2) + '\n')
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    passed = sum(item['passed'] for item in results)
    print(f'{passed}/{len(results)} checks passed; evidence: {out}')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
