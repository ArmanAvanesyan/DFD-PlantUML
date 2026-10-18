# Changelog

## 0.2.0 — candidate (publication pending)

- Consolidate the official Level 0–1 library around the published macro signatures, with matching local dependencies and commit-pinned remote dependencies.
- Repair optional titles and IDs, text escaping, customization setters, and structural validation. Validation remains opt-in.
- Restore legacy single-backslash `\n` line breaks in labels and titles. A doubled backslash preserves literal `\n`; actual line-break characters are also supported.
- Adopt explicit `@startdot` wrappers for both tested renderers; document the current PlantUML wrapper and SVG security-profile requirements. Legacy `@startuml` remains supported on the baseline renderer.
- Add compatibility coverage for legacy calls and text escaping, a pinned renderer matrix, SVG and PNG checks, and offline archive verification.
- Add a migration guide, source provenance, executable examples, and a reproducible distribution with file checksums.
- Document installation, the public API, compatibility, architecture, and stdlib status while retaining the three root library files as canonical sources.
- Organize compatibility cases into named positive and negative fixtures with explicit diagnostics; check documentation links in both the repository and extracted distribution.
- Add a deterministic, committed-revision stdlib preview export with source hashes and an explicit payload allowlist.
- Build an actual candidate PlantUML JAR with the proposed DFD namespace; check offline bundled/local parity, native SVG/PNG output, and the official JAR's missing-namespace negative control.
- Prepare proposed 0.2.0 release notes, committed candidate metadata, and a local-only contribution patch workflow; publication and upstream submission remain separate decisions.

Version 0.2.0 is proposed for the compatible functional consolidation of Level 0–1. This is an undated candidate entry, not a published release or a 1.0 stability claim. Publication remains a separate manual decision after the candidate passes the release gate.

## Historical `v0.1.0`

The retained tag points to `baa344fe1ec1b4a20486a47f06796183f1ccf16e`; its three library files are empty. It is not a functional compatibility baseline. The usable pre-consolidation `main` commit, `a09a92dc89b31b7e21f1c40b956714ff0789dabc`, supplies the published API reference. See [baseline evidence](https://github.com/ArmanAvanesyan/DFD-PlantUML/blob/main/docs/BASELINE.md).
