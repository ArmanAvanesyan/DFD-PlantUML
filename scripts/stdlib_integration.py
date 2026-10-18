#!/usr/bin/env python3
"""Build and verify a real DFD-enabled candidate JAR; never publish anything."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from check import inspect_png, inspect_svg, load_cases
from toolchain import load, prepare

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / 'scripts/stdlib-lock.json'
SVG = '{http://www.w3.org/2000/svg}'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def run(command, log, timeout=3600):
    """Retain commands and complete diagnostics even on failure."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as stream:
        stream.write(json.dumps(command) + '\n')
        stream.flush()
        proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f'Command failed ({proc.returncode}); see {log}')


def checkout(spec, target, logs):
    if not re.fullmatch('[a-f0-9]{40}', spec['revision']):
        raise ValueError('Upstream revision must be a full commit SHA')
    if target.exists():
        shutil.rmtree(target)
    run(['git', 'init', str(target)], logs / (target.name + '-init.log'))
    run(['git', '-C', str(target), 'fetch', '--depth=1', spec['repository'], spec['revision']],
        logs / (target.name + '-fetch.log'))
    run(['git', '-C', str(target), 'checkout', '--detach', 'FETCH_HEAD'], logs / (target.name + '-checkout.log'))
    actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != spec['revision']:
        raise ValueError('Fetched source revision mismatch')


def jar_manifest_version(path):
    with zipfile.ZipFile(path) as archive:
        manifest = archive.read('META-INF/MANIFEST.MF').decode('utf-8')
    unfolded = manifest.replace('\r\n ', '').replace('\n ', '')
    match = re.search(r'^Implementation-Version: ([^\r\n]+)', unfolded, re.M)
    if not match:
        raise ValueError('Candidate manifest lacks Implementation-Version')
    return match.group(1)


def resources_in_jar(jar, expected):
    with zipfile.ZipFile(jar) as archive:
        for name, fingerprint in expected.items():
            content = archive.read('stdlib/' + name)
            if hashlib.sha256(content).hexdigest() != fingerprint:
                raise ValueError('Candidate JAR resource mismatch: ' + name)
        if b'dfd' not in archive.read('stdlib/home.spm').splitlines():
            raise ValueError('Candidate namespace index omits dfd')


def docker(image, lock, out, args, *, online=False, build=False, candidate=None):
    # Offline render mounts only staged candidate, fixtures and three local files.
    mounts = ['-v', f'{out}:/work', '-v', f'{ROOT / "scripts"}:/harness:ro']
    if candidate:
        mounts += ['-v', f'{candidate}:/candidate.jar:ro']
    if build:
        cache = ROOT / 'build/stdlib-gradle-cache'
        cache.mkdir(parents=True, exist_ok=True)
        mounts += ['-v', f'{cache}:/gradle']
    return ['docker', 'run', '--rm', '--platform', lock['platform'], '--network',
            'bridge' if online else 'none', '-e', 'PLANTUML_SECURITY_PROFILE=UNSECURE',
            *mounts, '-w', '/work', '--entrypoint', 'sh', image, *args]


def build(out, revision, lock, image, runtime, builder, metadata=None):
    logs = out / 'logs'
    run([sys.executable, str(ROOT / 'scripts/stdlib.py'), 'export', '--revision', revision,
         '--output', str(out / 'export'), *(['--metadata', metadata] if metadata else [])], logs / 'export.log')
    export = out / 'export'
    for key in ['stdlib', 'plantuml']:
        checkout(lock[key], out / 'sources' / key, logs)
    encoder = out / 'sources/stdlib'
    shutil.copytree(export / 'dfd', encoder / 'stdlib/dfd')
    command = docker(builder, runtime, out, ['/harness/stdlib-integration/build.sh', 'stdlib', *lock['encoder_command']], online=True, build=True)
    run(docker(builder, runtime, out, ['-c', 'java -version; javac -version; dot -V']), logs / 'builder-versions.log')
    run(command, logs / 'encoder.log')
    output = encoder / 'output'
    payload = sorted((output / 'dfd').rglob('*'))
    files = [p for p in payload if p.is_file()] + [output / 'home.spm']
    if not files or not (output / 'dfd/puml.spm').exists() or b'dfd' not in (output / 'home.spm').read_bytes().splitlines():
        raise ValueError('Encoder did not produce DFD PUML resources')
    target = out / 'sources/plantuml/src/main/resources/stdlib'
    before = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
    for path in files:
        dest = target / path.relative_to(output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    resources = {p.relative_to(output).as_posix(): digest(p) for p in files}
    after = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
    changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    if changed - resources.keys():
        raise ValueError('Integration changed unrelated stdlib resources: ' + repr(changed - resources.keys()))
    command = docker(builder, runtime, out, ['/harness/stdlib-integration/build.sh', 'plantuml', *lock['jar_command']], online=True, build=True)
    run(command, logs / 'jar.log')
    jars = list((out / 'sources/plantuml/build/libs').glob('*.jar'))
    if len(jars) != 1:
        raise ValueError('Expected exactly one built GPL JAR: ' + repr(jars))
    shutil.copyfile(jars[0], out / 'candidate.jar')
    resources_in_jar(out / 'candidate.jar', resources)
    write_json(out / 'build-provenance.json', {
        'source_revision': revision, 'metadata': metadata, 'lock': lock, 'runtime': dict(runtime, prepared_image=image, builder_image=builder),
        'export_files': {p.relative_to(export).as_posix(): digest(p) for p in sorted(export.rglob('*')) if p.is_file()},
        'resources': resources, 'unchanged_stdlib_resources': {name: value for name, value in before.items() if name not in resources}, 'jar_sha256': digest(out / 'candidate.jar'),
        'commands': {'encoder': lock['encoder_command'], 'jar': lock['jar_command']},
        'harness_sha256': {p.relative_to(ROOT).as_posix(): digest(p) for p in [Path(__file__), LOCK_PATH, ROOT / 'scripts/toolchain.py', ROOT / 'scripts/toolchain-current.json', ROOT / 'scripts/Dockerfile', ROOT / 'scripts/check.py', *sorted((ROOT / 'scripts/stdlib-integration').glob('*'))] if p.is_file()},
        'build_scope': 'Java SPM encoder and GPL JAR; unrelated JS/TeaVM outputs excluded',
    })


def bundled(source):
    return re.sub(r'!include (?:\.\./)+((?:DFD)[A-Za-z_0-9]*?)\.puml', r'!include <dfd/\1>', source)


def canonical_dot(data):
    """Ignore only empty lines outside quoted strings; retain all other bytes."""
    quoted = escaped = False
    output = []
    for line in data.decode('utf-8').splitlines(keepends=True):
        if line.strip() or quoted:
            output.append(line)
        for char in line:
            if escaped:
                escaped = False
            elif char == chr(92) and quoted:
                escaped = True
            elif char == chr(34):
                quoted = not quoted
    return ''.join(output).encode('utf-8')


def check_case_names(cases):
    reserved = set()
    for case in cases:
        for index in range(case['output_count']):
            name = case['name'] + ('' if index == 0 else '_' + str(index).zfill(3))
            if name in reserved:
                raise ValueError('Duplicate integration artifact name: ' + name)
            reserved.add(name)


def semantic(path):
    root = ET.parse(path).getroot()
    # Ignore generator comments and graph title (source filename); retain all
    # visible node/edge text, directions and styles, including arrow polygons.
    graph = next(g for g in root.iter(SVG + 'g') if g.get('class') == 'graph')
    return [(node.tag.removeprefix(SVG), tuple(sorted(node.attrib.items())), node.text)
            for group in graph.findall(SVG + 'g') for node in group.iter()]


def behavior(name, dot, svg):
    tokens = {
        'flow_directions': ['dir=forward', 'dir=back', 'dir=both'],
        'optional_ids': ['E1 | User', '<f0>D2'],
        'styles': ['fillcolor="#ABCDEF"', 'color="#123456"', 'width=3 height=2'],
        'customization': ['rankdir=TB', 'width=2.5 height=1.2', 'COLOR="#234567"', 'COLOR="#345678"'],
    }
    if not all(token in dot for token in tokens.get(name, [])):
        return False
    if name == 'styles' and dot.count('style="dashed" color="#AA0000" penwidth=3') != 3:
        return False
    text = ' '.join(ET.parse(svg).getroot().itertext())
    if name == 'special_labels':
        return all(token in text for token in ['Quotes "yes"', '& <tags> {x|y}', 'café', 'Հայերեն', 'first', 'second'])
    return True


def missing_namespace(diagnostic):
    # Current SPM loader reports the absent namespace resource, followed by
    # a generic Fatal parsing error SVG; require the precise root cause.
    return bool(re.search(r'FileNotFoundException:\s*stdlib/dfd/info\.spm', diagnostic)
                or re.search(r'(cannot|can.t|unable).*include.*dfd/', diagnostic, re.I))


def rejection(proc, paths, expected, name):
    messages = []
    for path in paths:
        try:
            texts = [''.join(e.itertext()) for e in ET.parse(path).getroot().iter(SVG + 'text')]
            messages += texts[-1:]
        except (OSError, ET.ParseError):
            if name == 'reject_graphviz' and path.exists():
                messages.append(path.read_text(errors='replace'))
    if name == 'reject_graphviz':
        matched = any('syntax error' in m.lower() and 'error:' in m.lower() for m in messages)
    elif name == 'legacy_uml':
        matched = any('Syntax Error' in m or 'Please use @startdot' in m for m in messages)
    else:
        matched = any('Assertion error' in m and expected in m for m in messages)
    return matched and (proc.returncode != 0 or any(inspect_svg(p) for p in paths))


def validate(out, revision, lock, image, runtime, metadata=None):
    provenance = json.loads((out / 'build-provenance.json').read_text())
    if provenance['source_revision'] != revision or provenance['lock'] != lock or provenance.get('metadata') != metadata:
        raise ValueError('Candidate provenance does not match requested inputs')
    if digest(out / 'candidate.jar') != provenance['jar_sha256']:
        raise ValueError('Candidate JAR hash mismatch')
    resources_in_jar(out / 'candidate.jar', provenance['resources'])
    stage = out / 'validation'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copyfile(out / 'candidate.jar', stage / 'candidate.jar')
    for name in ['DFD.puml', 'DFD_Level_0.puml', 'DFD_Level_1.puml']:
        content = subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + name])
        (stage / name).write_bytes(content)
    snapshot = out / 'committed-inputs'
    if snapshot.exists():
        shutil.rmtree(snapshot)
    snapshot.mkdir()
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', revision], text=True).splitlines()
    for name in tracked:
        if name.startswith(('tests/fixtures/', 'examples/')) or name == 'README.md':
            dest = snapshot / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + name]))
    cases = load_cases('current', snapshot / 'tests/fixtures')
    for source in sorted((snapshot / 'examples').glob('*.puml')):
        cases.append({'name': source.stem, 'source': source.read_text().replace('../DFD_', '../../DFD_'), 'bundled_source': '@startdot\n!include <dfd/_examples_/' + source.stem + '>\n@enddot\n', 'expected_diagnostic': None, 'output_count': 1})
    readme = (snapshot / 'README.md').read_text()
    installation = re.findall(r'```text\n(@startdot\n.*?)```', readme, re.S)
    if len(installation) != 1:
        raise ValueError('Missing documented installation example')
    cases.append({'name': 'installation', 'source': re.sub(r'^!\$DFD_ROOT = .*\n', '', installation[0], flags=re.M).replace('!includeurl $DFD_ROOT/', '!include ../../'), 'expected_diagnostic': None, 'output_count': 1})
    check_case_names(cases)
    results = []
    commands = []
    write_json(stage / 'runtime.json', {
        'source_revision': revision, 'jar_sha256': digest(stage / 'candidate.jar'),
        'runtime': dict(runtime, prepared_image=image), 'upstream_sources': {name: lock[name] for name in ('stdlib', 'plantuml')},
        'harness_sha256': digest(Path(__file__)),
        'network': 'none', 'bundled_source_mount': False,
        'dot_comparison': 'Remove only empty lines outside quoted strings; retain raw files and hashes',
    })

    def invoke(args, mount, log):
        command = docker(image, runtime, mount, args, candidate=stage / 'candidate.jar')
        proc = subprocess.run(command, capture_output=True, text=True, timeout=90)
        log.write_text(proc.stdout + proc.stderr)
        commands.append({'command': command, 'returncode': proc.returncode,
                         'diagnostics': log.relative_to(stage).as_posix()})
        write_json(stage / 'commands.json', commands)
        return proc

    for mode in ['local', 'bundled']:
        folder = stage / 'cases' / mode
        folder.mkdir(parents=True)
        for case in cases:
            source = case.get('bundled_source', bundled(case['source'])) if mode == 'bundled' else case['source']
            (folder / (case['name'] + '.puml')).write_text(source)
    versions = invoke(['/harness/stdlib-integration/render.sh', '-version'], stage / 'cases/bundled', stage / 'candidate-version.log')
    manifest_version = jar_manifest_version(stage / 'candidate.jar')
    if versions.returncode or manifest_version != runtime['plantuml'] or 'PlantUML version ' not in versions.stdout:
        raise ValueError('Candidate manifest version differs from the pinned runtime contract')
    runtime_record = json.loads((stage / 'runtime.json').read_text())
    runtime_record.update(candidate_manifest_version=manifest_version, candidate_reported_version=versions.stdout.splitlines()[0])
    write_json(stage / 'runtime.json', runtime_record)
    # Official image does not contain our candidate library. A control that
    # succeeds unexpectedly invalidates the claim that this tests new resources.
    control_dir = stage / 'control'
    control_dir.mkdir()
    control = control_dir / 'negative-control.puml'
    control.write_text('@startdot\n!include <dfd/DFD_Level_0>\nstartDfd()\nProcess(P, "Control")\nendDfd()\n@enddot\n')
    proc = invoke(['-c', 'java -jar /opt/plantuml.jar -tsvg negative-control.puml'], control_dir, stage / 'negative-control.log')
    (stage / 'negative-control.log').write_text(proc.stdout + proc.stderr)
    invalid = inspect_svg(control.with_suffix('.svg'))
    diagnostic = proc.stdout + proc.stderr
    if control.with_suffix('.svg').exists():
        diagnostic += ' '.join(ET.parse(control.with_suffix('.svg')).getroot().itertext())
    if not missing_namespace(diagnostic):
        raise ValueError('Official negative control failed without a missing-include diagnostic')
    if proc.returncode == 0 and invalid is None:
        raise ValueError('Unmodified official JAR unexpectedly renders dfd')
    results.append({'case': 'official_jar_negative_control', 'passed': bool(invalid), 'diagnostics': proc.stdout + proc.stderr})
    for case in cases:
        passed = True
        for mode in ['local', 'bundled']:
            path = stage / 'cases' / mode / (case['name'] + '.puml')
            mount = stage if mode == 'local' else path.parent
            rel = path.relative_to(mount).as_posix()
            args = ['/harness/stdlib-integration/render.sh', '-charset', 'UTF-8', '-tsvg', rel]
            proc = invoke(args, mount, path.with_suffix('.log'))
            path.with_suffix('.log').write_text(proc.stdout + proc.stderr)
            svgs = sorted(p for p in path.parent.glob(path.stem + '*.svg') if re.fullmatch(re.escape(path.stem) + r'(?:_[0-9]+)?', p.stem))
            expected = case['expected_diagnostic']
            if expected:
                ok = rejection(proc, svgs, expected, case['name'])
            else:
                ok = proc.returncode == 0 and len(svgs) == case['output_count'] and not any(inspect_svg(p) for p in svgs)
                ok = ok and not re.search(r'suppressed|Exception|Some diagram description contains errors', proc.stdout + proc.stderr, re.I)
                if ok:
                    pre = invoke(['/harness/stdlib-integration/render.sh', '-charset', 'UTF-8', '-preproc', rel], mount, path.with_suffix('.preproc.log'))
                    path.with_suffix('.preproc.log').write_text(pre.stdout + pre.stderr)
                    ok = pre.returncode == 0 and path.with_suffix('.preproc').exists()
                    if ok:
                        ok = behavior(case['name'], path.with_suffix('.preproc').read_text(), svgs[0])
                if ok and case['name'] in ['level_0', 'level_1', 'customization', 'installation']:
                    png = invoke(['/harness/stdlib-integration/render.sh', '-charset', 'UTF-8', '-tpng', rel], mount, path.with_suffix('.png.log'))
                    path.with_suffix('.png.log').write_text(png.stdout + png.stderr)
                    ok = png.returncode == 0 and inspect_png(path.with_suffix('.png')) is None
                    ok = ok and not re.search(r'Exception|Error:|Some diagram description contains errors', png.stdout + png.stderr)
            results.append({'case': case['name'], 'mode': mode, 'passed': bool(ok), 'source_sha256': digest(path), 'expected_diagnostic': expected, 'diagnostics': path.with_suffix('.log').relative_to(stage).as_posix()})
            passed = passed and ok
        if passed and not case['expected_diagnostic']:
            local = stage / 'cases/local' / case['name']
            remote = stage / 'cases/bundled' / case['name']
            left_pre = sorted(p for p in local.parent.glob(local.name + '*.preproc') if re.fullmatch(re.escape(local.name) + r'(?:_[0-9]+)?', p.stem))
            right_pre = sorted(p for p in remote.parent.glob(remote.name + '*.preproc') if re.fullmatch(re.escape(remote.name) + r'(?:_[0-9]+)?', p.stem))
            # PlantUML releases may combine graphs into one preprocessor output
            # or emit numbered files; compare every emitted output either way.
            same = len(left_pre) == len(right_pre) and len(left_pre) in (1, case['output_count'])
            for left_dot, right_dot in zip(left_pre, right_pre):
                left_canonical = canonical_dot(left_dot.read_bytes())
                right_canonical = canonical_dot(right_dot.read_bytes())
                left_dot.with_suffix('.canonical.dot').write_bytes(left_canonical)
                right_dot.with_suffix('.canonical.dot').write_bytes(right_canonical)
                same = same and left_canonical == right_canonical
            for index in range(case['output_count']):
                suffix = '' if index == 0 else '_' + str(index).zfill(3)
                left = local.with_name(local.name + suffix)
                right = remote.with_name(remote.name + suffix)
                same = same and semantic(left.with_suffix('.svg')) == semantic(right.with_suffix('.svg'))
            results.append({'case': case['name'], 'mode': 'expanded_dot_and_semantics', 'passed': bool(same)})
    write_json(stage / 'results.json', results)
    write_json(stage / 'artifacts.json', {p.relative_to(stage).as_posix(): digest(p) for p in sorted(stage.rglob('*')) if p.is_file()})
    failed = [r for r in results if not r['passed']]
    print(f'{len(results) - len(failed)}/{len(results)} integration checks passed; {stage}', flush=True)
    if failed:
        raise RuntimeError('Integration failures: ' + json.dumps(failed))


def prepare_builder(out, image, lock, runtime):
    if not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', lock['jdk_image']):
        raise ValueError('JDK image must be digest-pinned')
    recipe = ROOT / 'scripts/stdlib-integration/Dockerfile'
    fingerprint = hashlib.sha256(recipe.read_bytes() + image.encode() + lock['jdk_image'].encode()).hexdigest()
    tag = 'dfd-stdlib-builder:' + fingerprint
    runtime_tag = 'dfd-stdlib-runtime:' + image.removeprefix('sha256:')
    run(['docker', 'tag', image, runtime_tag], out / 'logs/runtime-tag.log')
    run(['docker', 'build', '--platform', runtime['platform'], '--build-arg', 'JDK_IMAGE=' + lock['jdk_image'],
         '--build-arg', 'RENDER_IMAGE=' + runtime_tag, '-f', str(recipe), '-t', tag, str(recipe.parent)], out / 'logs/builder.log')
    return subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--metadata', help='Optional version JSON path in the selected committed revision')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/stdlib-integration')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--verify', args.revision + '^{commit}'], text=True).strip()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'build'):
        parser.error('--output must be below the ignored build directory')
    out.mkdir(parents=True, exist_ok=True)
    lock = json.loads(LOCK_PATH.read_text())
    runtime = load('current')
    image = prepare(runtime)
    if not args.validate_only:
        builder = prepare_builder(out, image, lock, runtime)
        build(out, revision, lock, image, runtime, builder, args.metadata)
    validate(out, revision, lock, image, runtime, args.metadata)


if __name__ == '__main__':
    main()
