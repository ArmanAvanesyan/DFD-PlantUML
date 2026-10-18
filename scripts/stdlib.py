#!/usr/bin/env python3
"""Export and verify a deterministic stdlib contribution from committed inputs."""
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


def committed_file(repo, commit, name):
    if not isinstance(name, str) or not name or name.startswith('/') or '\\' in name or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Expected a repository-relative committed input path')
    tree = git(repo, 'ls-tree', '-z', commit, '--', ':(literal)' + name).split(b'\0')[0]
    if not tree or tree.split(b' ', 1)[0] != b'100644':
        raise ValueError('Missing or non-regular committed input: ' + name)
    return git(repo, 'show', commit + ':' + name)


def committed_inputs(repo, revision):
    commit = git(repo, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Expected a full SHA-1 commit')
    files = {}
    for name in INPUTS:
        files[name] = committed_file(repo, commit, name)
    return commit, files


def submission_version(data):
    def unique_fields(pairs):
        fields = {}
        for key, value in pairs:
            if key in fields:
                raise ValueError('Duplicate submission metadata field: ' + key)
            fields[key] = value
        return fields
    fields = json.loads(data.decode('utf-8'), object_pairs_hook=unique_fields)
    if not isinstance(fields, dict) or set(fields) != {'version'} or not isinstance(fields['version'], str):
        raise ValueError('Submission metadata requires exactly one string version field')
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', fields['version']):
        raise ValueError('Submission metadata version must be stable SemVer MAJOR.MINOR.PATCH')
    return fields['version']


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


def build_export(repo, revision='HEAD', metadata=None):
    commit, sources = committed_inputs(repo, revision)
    version = 'unreleased'
    metadata_info = {'mode': 'preview', 'version': version}
    if metadata is not None:
        metadata = str(metadata)
        data = committed_file(repo, commit, metadata)
        version = submission_version(data)
        sources[metadata] = data
        metadata_info = {'mode': 'submission-candidate', 'version': version,
                         'source': metadata, 'sha256': digest(data)}
    license_text = sources['LICENSE'].decode('utf-8')
    if not license_text.startswith('MIT License\n'):
        raise ValueError('Expected committed MIT license')
    header = ("' Exported candidate; canonical sources remain in DFD-PlantUML.\n" +
              ''.join(("' " + line if line else "'") + '\n' for line in license_text.splitlines()) + '\n').encode()
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
    if metadata is not None:
        if readme.count('\nversion: unreleased\n') != 1:
            raise ValueError('Expected exactly one literal preview version field')
        readme = readme.replace('\nversion: unreleased\n', '\nversion: ' + version + '\n', 1)
    output['dfd/README.md'] = readme.encode()
    transforms['dfd/README.md'] = ['substitute committed source SHA into preview metadata template']
    if metadata is not None:
        transforms['dfd/README.md'].append('substitute stable version from explicitly selected committed metadata')
    for name, data in output.items():
        if name.endswith('.puml'):
            validate_includes(name, data)
    manifest = {'schema': 1, 'source_repository': REPOSITORY, 'source_commit': commit, 'metadata': metadata_info,
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


def check_export(repo, revision, output, metadata=None):
    files = build_export(repo, revision, metadata)
    if files != build_export(repo, revision, metadata):
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
        command.add_argument('--metadata', help='Repository-relative JSON file from --revision containing exactly a stable version field')
        command.add_argument('--output', type=Path, default=Path('build/stdlib'))
    args = parser.parse_args()
    if args.command == 'export':
        files = build_export(ROOT, args.revision, args.metadata)
        write_export(files, args.output)
    else:
        files = check_export(ROOT, args.revision, args.output, args.metadata)
    print(f'{args.command}: {len(files) - 1} contribution files; manifest: {args.output / "MANIFEST.json"}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
