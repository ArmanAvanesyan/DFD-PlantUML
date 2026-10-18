#!/usr/bin/env python3
"""Prepare a local review patch; never push, submit, tag, or publish."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from stdlib import ROOT, build_export, git

SECTION = '''## DFD-PlantUML [dfd]

DFD-PlantUML provides Level 0 context diagrams and Level 1 data-flow diagrams.
Its maintained source and API documentation are in
[ArmanAvanesyan/DFD-PlantUML](https://github.com/ArmanAvanesyan/DFD-PlantUML).
See [contribution metadata](./stdlib/dfd/README.md) and
[examples](./stdlib/dfd/_examples_).

The library emits DOT: use `@startdot` / `@enddot` and Graphviz.
Native SVG in the tested engine requires `PLANTUML_SECURITY_PROFILE=UNSECURE`;
the integration suite applies it to trusted inputs in network-disabled containers.
These includes become available only in a PlantUML build containing this contribution.

```plantuml
@startdot
!include <dfd/DFD_Level_0>
startDfd("Loan System")
External(Customer, "Customer")
Process(System, "Loan System")
Flow(Customer, System, "application")
Flow_Back(Customer, System, "decision")
endDfd()
@enddot
```

'''


def catalog(readme):
    anchor = '## Domain Story library (DomainStory-PlantUML) [DomainStory]\n'
    toc = '  - [Domain Story library (DomainStory-PlantUML) [DomainStory]]'
    if '## DFD-PlantUML [dfd]' in readme or readme.count(anchor) != 1 or readme.count(toc) != 1:
        raise ValueError('Unexpected catalog layout or existing DFD entry; review upstream changes')
    readme = readme.replace(toc, '  - [DFD-PlantUML [dfd]](#dfd-plantuml-dfd)\n' + toc, 1)
    return readme.replace(anchor, SECTION + anchor, 1)


def prepare(repo, revision, upstream, output, metadata=None):
    for path in (Path(output), *Path(output).parents):
        if path.is_symlink():
            raise ValueError('Review output must not use symlinks')
    upstream, output = Path(upstream).resolve(), Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Review output must be a new or empty directory')
    if output.is_relative_to(upstream):
        raise ValueError('Review output must remain outside the upstream checkout')
    commit = git(repo, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}').decode().strip()
    lock = json.loads(git(repo, 'show', commit + ':scripts/stdlib-lock.json'))
    base = lock['stdlib']['revision']
    if git(upstream, 'rev-parse', 'HEAD').decode().strip() != base or git(upstream, 'status', '--porcelain'):
        raise ValueError('Upstream checkout must be clean at the locked stdlib revision')
    if git(upstream, 'ls-tree', base, '--', 'stdlib/dfd'):
        raise ValueError('DFD namespace already exists upstream; review rather than overwrite')
    files = build_export(repo, revision, metadata=metadata)
    original = git(upstream, 'show', base + ':README.md')
    updated = catalog(original.decode()).encode()
    with tempfile.TemporaryDirectory(prefix='dfd-contribution-') as tmp:
        root = Path(tmp)
        git(root, 'init', '-q')
        (root / 'README.md').write_bytes(original)
        git(root, 'add', 'README.md')
        tree = git(root, 'write-tree').decode().strip()
        (root / 'README.md').write_bytes(updated)
        for name, data in files.items():
            if name.startswith('dfd/'):
                dest = root / 'stdlib' / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        git(root, 'add', '.')
        patch = git(root, '-c', 'core.quotePath=false', 'diff', '--cached', '--binary', tree, '--', '.')
    output.mkdir(parents=True, exist_ok=True)
    patch_path = output / 'contribution.patch'
    patch_path.write_bytes(patch)
    # Check against the genuine checkout, without changing it or its index.
    git(upstream, 'apply', '--check', str(patch_path))
    payload = {'README.md': updated, **{'stdlib/' + n: data for n, data in files.items() if n.startswith('dfd/')}}
    manifest = {'source_commit': commit, 'stdlib_revision': base, 'submission_status': 'local-review-only',
                'preparer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'patch_sha256': hashlib.sha256(patch).hexdigest(),
                'files': {n: hashlib.sha256(data).hexdigest() for n, data in sorted(payload.items())},
                'export_manifest': json.loads(files['MANIFEST.json'])}
    (output / 'REVIEW.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    (output / 'REVIEW.md').write_text(
        '# Local stdlib contribution review\n\n'
        f'Source: `{commit}`. Upstream base: `{base}`.\n\n'
        'The patch passed `git apply --check` against the clean pinned upstream checkout. '
        'It contains only the root catalog edit and seven generated DFD files. '
        'The manifest is outside the contribution. No fork, push, PR, tag, or release was created.\n\n'
        'Default metadata is unreleased and requires review before submission. '
        'An explicit committed metadata selection also requires maintainer acceptance; '
        'it is not proof of publication. Review generated source, metadata, examples, '
        'DOT/SVG requirements and matching candidate validation evidence before any submission.\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--upstream', required=True, type=Path, help='Clean checkout at the locked stdlib revision')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/stdlib-submission')
    parser.add_argument('--metadata', help='Optional version JSON path in the selected committed revision')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'build'):
        parser.error('--output must remain below the ignored build directory')
    try:
        result = prepare(ROOT, args.revision, args.upstream, args.output, args.metadata)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, str(exc) + '\n')
    print('Prepared local review patch: ' + str(args.output / 'contribution.patch'))
    print('SHA256: ' + result['patch_sha256'])


if __name__ == '__main__':
    main()
