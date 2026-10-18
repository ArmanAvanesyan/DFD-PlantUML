#!/usr/bin/env python3
"""Render compatibility fixtures in the digest-pinned toolchain; stdlib only."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'scripts/toolchain.json').read_text())


def docker(args, online=False, entrypoint=None):
    mount = ROOT / 'build/remote' if online else ROOT
    command = ['docker', 'run', '--rm', '--platform', LOCK['platform'],
               '--network', 'bridge' if online else 'none',
               '-e', 'PLANTUML_SECURITY_PROFILE=UNSECURE' if online else 'PLANTUML_SECURITY_PROFILE=LEGACY',
               '-v', f'{mount}:/work', '-w', '/work']
    if online:
        command += ['-v', f'{ROOT / "scripts"}:/harness:ro']
    command += ['--entrypoint', entrypoint or 'sh']
    if not entrypoint:
        args = ['/harness/render.sh' if online else '/work/scripts/render.sh'] + args
    return subprocess.run(command + [LOCK['image']] + args, text=True, capture_output=True, timeout=90)


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


def fixture(directory, name, level, body, expected=None, prelude=''):
    path = directory / (name + '.puml')
    path.write_text(f'@startuml\n!include ../../DFD_Level_{level}.puml\n{prelude}\n{body}\n@enduml\n')
    return path, expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote-ref', help='40-character commit in the official repository')
    args = parser.parse_args()
    if args.remote_ref and not re.fullmatch('[0-9a-f]{40}', args.remote_ref):
        parser.error('--remote-ref must be a full lowercase commit SHA')
    out = ROOT / 'build' / ('remote' if args.remote_ref else 'checks')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    versions = docker(['-c', 'java -version; dot -V; java -jar /opt/plantuml.jar -version'], entrypoint='sh')
    (out / 'toolchain.log').write_text(versions.stdout + versions.stderr)
    if versions.returncode:
        sys.exit(versions.stderr)
    cases = []
    for source in sorted((ROOT / 'examples').glob('*.puml')):
        dest = out / source.name
        dest.write_text(source.read_text().replace('../DFD_', '../../DFD_'))
        cases.append((dest, None))
    installation = re.findall(r"```text\n(@startuml\n.*?)```", (ROOT / 'README.md').read_text(), re.S)
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
            fixture(out, 'backslash', 0, '''!$label = "C:" + %chr(92) + "temp"
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
        # A second @startuml must have independent globals and output, even for the same aliases.
        multi = out / 'multiple.puml'
        multi.write_text(('''@startuml
!include ../../DFD_Level_0.puml
SetValidation(1)
startDfd()
Process(P, "System")
endDfd()
@enduml
''') * 2)
        cases.append((multi, None))
    else:
        prefix = f'https://raw.githubusercontent.com/ArmanAvanesyan/DFD-PlantUML/{args.remote_ref}/'
        for path, _ in cases:
            path.write_text(path.read_text().replace('@startuml\n', '@startuml\n!$DFD_ROOT = ' + json.dumps(prefix.rstrip('/')) + '\n').replace('!include ../../', '!includeurl $DFD_ROOT/'))
    readme_blocks = re.findall(r"```plantuml\n(.*?)```", (ROOT / 'README.md').read_text(), re.S)
    example_blocks = [p.read_text() for p in sorted((ROOT / 'examples').glob('*.puml'))]
    if sorted(readme_blocks) != sorted(example_blocks):
        sys.exit('README examples differ from executable examples')
    results = []
    for path, expected in cases:
        rel = path.name if args.remote_ref else path.relative_to(ROOT).as_posix()
        proc = docker(['-charset', 'UTF-8', '-tsvg', rel], online=bool(args.remote_ref))
        (path.with_suffix('.log')).write_text(proc.stdout + proc.stderr)
        svgs = sorted(out.glob(path.stem + '*.svg'))
        if expected:
            diagnostics = proc.stdout + proc.stderr
            for svg in svgs:
                diagnostics += svg.read_text(errors='replace')
            ok = expected in diagnostics and (proc.returncode != 0 or any(inspect_svg(p) for p in svgs))
            detail = 'expected rejection' if ok else diagnostics[:700]
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
                if path.stem == 'backslash':
                    ok = ok and 'C:\\temp' in ' '.join(ET.parse(svgs[0]).getroot().itertext())
                if not ok:
                    detail = 'preprocessor/output behavior assertion failed'
        results.append({'case': path.stem, 'passed': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + path.stem + ('' if ok else ': ' + detail))
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
