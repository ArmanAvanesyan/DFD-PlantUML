#!/usr/bin/env python3
"""Validate repository-local Markdown links, including archive-only installs."""
import os
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def prose(text):
    text = re.sub(r'^```.*?^```[^\n]*$', '', text, flags=re.M | re.S)
    return re.sub(r'`[^`\n]*`', '', text)


def anchors(text):
    found, counts = set(), {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(text), re.M):
        heading = re.sub(r'<[^>]+>', '', heading).lower()
        slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        found.add(slug + (f'-{index}' if index else ''))
    found.update(re.findall(r'<a\s+(?:name|id)=["\']([^"\']+)', text))
    return found


def check_links(files):
    """files maps POSIX paths to bytes (None is enough for non-Markdown files)."""
    errors = []
    for name, content in sorted(files.items()):
        if not name.endswith('.md') or content is None:
            continue
        for raw in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', prose(content.decode())):
            raw = raw.strip()
            target = raw[1:raw.find('>')] if raw.startswith('<') else raw.split()[0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            path = unquote(parsed.path)
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if resolved.startswith('../') or resolved.startswith('/') or resolved not in files:
                errors.append(f'{name}: missing local target {target}')
            elif parsed.fragment and resolved.endswith('.md'):
                if unquote(parsed.fragment) not in anchors(files[resolved].decode()):
                    errors.append(f'{name}: missing heading {target}')
    return errors


def require_links(files):
    errors = check_links(files)
    if errors:
        raise ValueError('Broken documentation links:\n' + '\n'.join(errors))


def repository_files(root=ROOT):
    files = {}
    for directory, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {'.git', 'build', '__pycache__'}]
        for name in names:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            files[relative] = path.read_bytes() if path.suffix == '.md' else None
    return files


if __name__ == '__main__':
    try:
        require_links(repository_files())
        print('PASS repository documentation links')
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
