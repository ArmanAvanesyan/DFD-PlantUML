#!/usr/bin/env python3
"""Export and verify a deterministic preview stdlib contribution from committed inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/ArmanAvanesyan/DFD-PlantUML'
LIBRARIES = ('DFD.puml', 'DFD_Level_0.puml', 'DFD_Level_1.puml')
EXAMPLES = ('level_0', 'level_1', 'customization')
TEMPLATE = 'packaging/stdlib/README.template.md'
INPUTS = LIBRARIES + tuple(f'examples/{name}.puml' for name in EXAMPLES) + ('LICENSE', TEMPLATE)
ROUTING = b'!ifdef $DFD_ROOT\n!include $DFD_ROOT/DFD.puml\n!else\n!include DFD.puml\n!endif\n'
METADATA = ('name', 'display_name', 'description', 'author', 'version', 'release', 'license', 'source', 'origin')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, stderr=subprocess.PIPE)


def committed_inputs(repo, revision):
    commit = git(repo, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Expected a full SHA-1 commit')
    files = {}
    for name in INPUTS:
        tree = git(repo, 'ls-tree', '-z', commit, '--', name).split(b'\0')[0]
        if not tree or tree.split(b' ', 1)[0] != b'100644':
            raise ValueError('Missing or non-regular committed input: ' + name)
        files[name] = git(repo, 'show', commit + ':' + name)
    return commit, files


def validate_includes(name, content):
    """Exported PlantUML may include only the explicit bundled namespace."""
    text = content.decode('utf-8')
    if 'https://raw.githubusercontent' in text:
        raise ValueError('Raw GitHub URL rejected by stdlib encoder in ' + name)
    for line in text.splitlines():
        if re.match(r'^\s*!include', line, re.I):
            if not re.fullmatch(r'!include <dfd/(DFD|DFD_Level_0|DFD_Level_1)>', line):
                raise ValueError('Unexpected or network-dependent include in ' + name)
    if '$DFD_ROOT' in text:
        raise ValueError('Remote include routing remains in ' + name)


def build_export(repo, revision='HEAD'):
    commit, sources = committed_inputs(repo, revision)
    license_text = sources['LICENSE'].decode('utf-8')
    if not license_text.startswith('MIT License\n'):
        raise ValueError('Expected committed MIT license')
    header = ("' Exported preview; canonical sources remain in DFD-PlantUML.\n" +
              ''.join("' " + line + '\n' for line in license_text.splitlines()) + '\n').encode()
    output = {}
    transforms = {}
    for name in LIBRARIES:
        data = sources[name]
        operations = ['prepend committed MIT license as PlantUML comments']
        if name != 'DFD.puml':
            if data.count(ROUTING) != 1:
                raise ValueError('Expected exactly one known profile routing block: ' + name)
            data = data.replace(ROUTING, b'!include <dfd/DFD>\n', 1)
            operations.append('replace exact local/remote core routing block with !include <dfd/DFD>')
        target = 'dfd/' + name
        output[target] = header + data
        transforms[target] = operations
    for example in EXAMPLES:
        source = f'examples/{example}.puml'
        data = sources[source]
        includes = re.findall(rb'^!include \.\./(DFD_Level_[01])\.puml$', data, re.M)
        if len(includes) != 1:
            raise ValueError('Expected exactly one known example include: ' + source)
        old = b'!include ../' + includes[0] + b'.puml\n'
        if data.count(old) != 1:
            raise ValueError('Unexpected example include line ending: ' + source)
        data = data.replace(old, b'!include <dfd/' + includes[0] + b'>\n', 1)
        target = f'dfd/_examples_/{example}.puml'
        output[target] = header + data
        transforms[target] = ['prepend committed MIT license as PlantUML comments', 'replace exact sibling profile include with bundled profile include']
    template = sources[TEMPLATE].decode('utf-8')
    if template.count('@REVISION@') != 1:
        raise ValueError('Metadata template requires exactly one @REVISION@')
    readme = template.replace('@REVISION@', commit)
    if not readme.startswith('---\n') or '\n---\n' not in readme[4:]:
        raise ValueError('Missing metadata frontmatter')
    fields = {}
    for line in readme.split('---\n', 2)[1].splitlines():
        key, separator, value = line.partition(':')
        if not separator or key in fields or not value.strip():
            raise ValueError('Invalid or duplicate metadata field: ' + line)
        fields[key] = value.strip()
    if set(fields) != set(METADATA) or fields['name'] != 'dfd' or fields['version'] != 'unreleased' or fields['release'] != REPOSITORY + '/tree/' + commit:
        raise ValueError('Missing or unexpected preview metadata')
    if fields['license'] != 'MIT' or fields['source'] != REPOSITORY or fields['origin'] != REPOSITORY:
        raise ValueError('Unexpected license or source metadata')
    output['dfd/README.md'] = readme.encode()
    transforms['dfd/README.md'] = ['substitute committed source SHA into preview metadata template']
    for name, data in output.items():
        if name.endswith('.puml'):
            validate_includes(name, data)
    manifest = {'schema': 1, 'source_repository': REPOSITORY, 'source_commit': commit,
                'inputs': {name: digest(data) for name, data in sorted(sources.items())},
                'files': {name: {'sha256': digest(data), 'transformations': transforms[name]} for name, data in sorted(output.items())}}
    output['MANIFEST.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    return output


def inspect_output(output):
    output = Path(output)
    # Resolve no symlinks: never follow an output path through a symlink.
    for path in (output, *output.parents):
        if path.is_symlink():
            raise ValueError('Symlink output path: ' + str(path))
    if not output.exists():
        return {}
    if not output.is_dir():
        raise ValueError('Output is not a directory')
    result = {}
    for path in output.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Non-regular output entry: ' + str(path))
        if path.is_dir():
            if path.relative_to(output).as_posix() not in ('dfd', 'dfd/_examples_'):
                raise ValueError('Unexpected output directory: ' + str(path))
        else:
            result[path.relative_to(output).as_posix()] = path.read_bytes()
    return result


def write_export(files, output):
    existing = inspect_output(output)
    if existing and existing != files:
        raise ValueError('Stale or unexpected output; choose an empty output directory')
    for name, content in sorted(files.items()):
        path = Path(output) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def check_export(repo, revision, output):
    files = build_export(repo, revision)
    if files != build_export(repo, revision):
        raise ValueError('Export is not reproducible')
    if inspect_output(output) != files:
        raise ValueError('Export is missing, stale, modified, or contains unexpected files')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('export', 'check'):
        command = sub.add_parser(name)
        command.add_argument('--revision', default='HEAD')
        command.add_argument('--output', type=Path, default=Path('build/stdlib'))
    args = parser.parse_args()
    if args.command == 'export':
        files = build_export(ROOT, args.revision)
        write_export(files, args.output)
    else:
        files = check_export(ROOT, args.revision, args.output)
    print(f'{args.command}: {len(files) - 1} contribution files; manifest: {args.output / "MANIFEST.json"}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
