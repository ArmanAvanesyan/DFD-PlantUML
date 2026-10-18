#!/usr/bin/env python3
"""Render compatibility fixtures in the digest-pinned toolchain; stdlib only."""
import argparse
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


def fixture(directory, name, level, body, expected=None, prelude=''):
    path = directory / (name + '.puml')
    path.write_text(f'@startdot\n!include ../../DFD_Level_{level}.puml\n{prelude}\n{body}\n@enddot\n')
    return path, expected


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
        cases += [
            fixture(out, 'empty_title', 0, 'startDfd()\nExternal(U, "User")\nProcess(P, "System")\nFlow(U, P)\nendDfd()'),
            fixture(out, 'optional_ids', 1, 'startDfd()\nExternal(U, "User", "E1")\nProcess("System")\nSubProcess(P, "1.1", "Work")\nDataStore(D, "Records", "D2")\nDataFlows()\nFlow(U, P)\nFlow(P, D)\nendDfd()'),
            fixture(out, 'permissive', 0, 'startDfd()\nProcess(P1, "One")\nProcess(P2, "Two")\nDataStore(D, "Records")\nFlow(P1, Undeclared)\nendDfd()'),
            fixture(out, 'repeat_include', 0, 'startDfd()\nExternal(U, "User")\nProcess(P, "System")\nFlow(U, P)\nendDfd()', prelude='!include ../../DFD_Level_0.puml\n!include ../../DFD.puml'),
            fixture(out, 'validated', 0, 'SetValidation(1)\nstartDfd()\nExternal(P10, "User")\nProcess(P1, "System")\nFlow(P10, P1)\nendDfd()'),
            fixture(out, 'styles', 0, 'SetAllComponentColors("#ABCDEF", "#123456", "#345678")\nSetAllComponentStyles("dashed")\nSetAllComponentSizes(3, 2)\nSetAllFlowProperties("dashed", "#AA0000", "#0000AA", 15, 3)\nstartDfd()\nExternal(U, "User")\nProcess(P, "System")\nFlow(U, P, "label")\nFlow_Back(P, U)\nBiFlow(U, P)\nendDfd()'),
            fixture(out, 'special_labels', 1, '''!$label = "Quotes " + %chr(34) + "yes" + %chr(34) + " & <tags> {x|y} café Հայերեն"
startDfd($label)
External(U, $label)
Process($label)
SubProcess(P, "1", $label)
DataStore(D, $label)
DataFlows()
Flow(U, P, $label)
!$multiline = "first" + %chr(10) + "second"
Flow(P, D, $multiline)
endDfd()'''),
            fixture(out, 'flow_directions', 0, 'startDfd()\nExternal(U, "Error: Syntax Error is a valid label")\nProcess(P, "System")\nFlow(U, P)\nFlow_Back(P, U, "backward")\nBiFlow(U, P)\nendDfd()'),
            fixture(out, 'legacy_newlines', 1, r'''startDfd("Title\nsecond")
External(U, "External\nsecond")
Process("Boundary\nsecond")
SubProcess(P, "1", "Process\nsecond")
DataStore(D, "Store\nsecond")
DataFlows()
Flow(U, P, "Flow\nsecond")
Flow(P, D)
endDfd()'''),
            fixture(out, 'literal_newlines', 0, r'''startDfd("Title\\nsecond")
External(U, "C:\\new")
Process(P, "Process\\nsecond")
Flow(U, P, "Flow\\nsecond")
endDfd()'''),
            fixture(out, 'backslash_paths', 0, '''!$slash = %chr(92)
!$unc = $slash + $slash + "server" + $slash + "share"
!$double = "path" + $slash + $slash + "tail"
!$trailing = "end" + $slash + $slash
!$single = "one" + $slash
startDfd($unc)
External(U, $unc)
Process(P, $double)
Flow(U, P, $trailing)
BiFlow(P, U, $single)
endDfd()'''),
            fixture(out, 'backslash',
 0, '''!$label = "C:" + %chr(92) + "temp"
startDfd()
External(U, $label)
Process(P, "System")
Flow(U, P, $label)
endDfd()'''),
            fixture(out, 'reject_second_process', 0, 'SetValidation(1)\nstartDfd()\nProcess(P1, "One")\nProcess(P2, "Two")\nendDfd()', 'DFD Level 0 allows only one process'),
            fixture(out, 'reject_datastore', 0, 'SetValidation(1)\nstartDfd()\nDataStore(D, "Records")\nendDfd()', 'Data stores are not allowed'),
            fixture(out, 'reject_substring', 0, 'SetValidation(1)\nstartDfd()\nExternal(P10, "User")\nProcess(System, "System")\nFlow(P1, System)\nendDfd()', 'Unknown flow source: P1'),
            fixture(out, 'reject_destination', 0, 'SetValidation(1)\nstartDfd()\nProcess(P, "System")\nFlow(P, Missing)\nendDfd()', 'Unknown flow destination: Missing'),
            fixture(out, 'reject_unclosed', 1, 'startDfd()\nProcess("System")\nendDfd()', 'Close the Level 1 boundary'),
            fixture(out, 'reject_graphviz', 0, 'startDfd()\nthis is invalid dot !!!\nendDfd()', 'syntax error'),
            fixture(out, 'reject_close', 1, 'startDfd()\nDataFlows()\nendDfd()', 'Boundary close requires'),
        ]
        # A second @startdot must have independent globals and output, even for the same aliases.
        multi = out / 'multiple.puml'
        multi.write_text(('''@startdot
!include ../../DFD_Level_0.puml
SetValidation(1)
startDfd()
Process(P, "System")
endDfd()
@enddot
''') * 2)
        cases.append((multi, None))
        legacy = out / 'legacy_uml.puml'
        legacy.write_text('@startuml\n!include ../../DFD_Level_0.puml\nstartDfd()\nProcess(P, "Legacy")\nendDfd()\n@enduml\n')
        cases.append((legacy, None if args.toolchain == 'baseline' else 'Syntax Error'))
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
            ok = proc.returncode == 0 and len(svgs) == (2 if path.stem == 'multiple' else 1) and not any(failures)
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
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    passed = sum(item['passed'] for item in results)
    print(f'{passed}/{len(results)} checks passed; evidence: {out}')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
