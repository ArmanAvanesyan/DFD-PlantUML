# Changelog

## Unreleased

- Consolidate the official Level 0–1 library around the published macro signatures, with matching local dependencies and commit-pinned remote dependencies.
- Repair optional titles and IDs, text escaping, customization setters, and structural validation. Validation remains opt-in.
- Restore legacy single-backslash `\n` line breaks in labels and titles. A doubled backslash preserves literal `\n`; actual line-break characters are also supported.
- Adopt explicit `@startdot` wrappers for both tested renderers; document the current PlantUML wrapper and SVG security-profile requirements. Legacy `@startuml` remains supported on the baseline renderer.
- Add compatibility coverage for legacy calls and text escaping, a pinned renderer matrix, SVG and PNG checks, and offline archive verification.
- Add a migration guide, source provenance, executable examples, and a reproducible distribution with file checksums.

No version is assigned to these changes yet. Release numbering and publication are separate manual decisions after the candidate passes the release gate.

## Historical `v0.1.0`

The retained tag points to `baa344fe1ec1b4a20486a47f06796183f1ccf16e`; its three library files are empty. It is not a functional compatibility baseline. The usable pre-consolidation `main` commit, `a09a92dc89b31b7e21f1c40b956714ff0789dabc`, supplies the published API reference. See [baseline evidence](https://github.com/ArmanAvanesyan/DFD-PlantUML/blob/main/docs/BASELINE.md).
