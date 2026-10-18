# DFD-PlantUML 0.2.0 — proposed release notes

Version **0.2.0** is selected for this release candidate; publication is pending. These notes do not announce a released artifact. The accepted source SHA and evidence belong in the candidate PR and must pass review before separately authorized publication.

The minor version identifies the functional Level 0–1 consolidation while preserving the published API. It does not claim a 1.0 stability milestone. The historical `v0.1.0` tag remains unchanged.

## Library and compatibility

The official repository provides a self-contained Level 0–1 library with one shared core and two profiles. The three root filenames, local sibling includes, `$DFD_ROOT` remote installation, published macro signatures, level-specific `Process` calls, and permissive defaults remain supported. Semantic validation remains opt-in.

The candidate repairs optional titles and IDs, label escaping, customization setters, and structural validation. Legacy single-backslash `\n` label/title breaks remain supported; doubled backslashes preserve literal text. See the [migration guide](MIGRATION.md) and [API contract](API.md) for precise behavior.

## Installation and verification

Use [local or commit-pinned remote installation](INSTALLATION.md). The distribution includes the library, license, examples, and linked user documentation, with deterministic packaging and per-file checksums. Named behavioral fixtures cover rendering and expected validation failures; both pinned toolchains check local, remote, and extracted-archive use.

Canonical examples use `@startdot` / `@enddot` and require Graphviz. Tested toolchains are PlantUML 1.2025.2 / Java 17 / Graphviz 12.2.1 and PlantUML 1.2026.9 / Java 21 / Graphviz 14.0.1. Legacy `@startuml` works on the baseline and is an expected upstream rejection on current PlantUML. Current native DOT SVG output requires `PLANTUML_SECURITY_PROFILE=UNSECURE`; validation applies it to trusted examples inside network-disabled containers. See [release preparation](RELEASING.md) for exact pins and commands.

## Stdlib preview and exclusions

A deterministic export and an actual locally built PlantUML candidate JAR demonstrate proposed `<dfd/...>` installation, offline bundled/local parity, and native SVG/PNG rendering. Existing official PlantUML releases do not ship this contribution. The committed submission metadata selects `0.2.0` for review; the default exporter mode remains `unreleased`. Local preparation does not submit anything upstream. See [stdlib status](STDLIB.md).

Level 2, alternate notations, and experimental APIs remain outside this candidate. The historical `v0.1.0` tag contains empty library files and is not the functional compatibility baseline. The proposed version is `0.2.0`; no tag or release is created by candidate preparation.
