# Preparing a release candidate

Publication is manual. This workflow prepares and checks an archive without creating a tag, GitHub release, or registry publication. Keep all checks on one candidate commit. Do not assign a version until compatibility, documentation, and distribution evidence have been reviewed.

## Supported renderer gate

The compatibility baseline is PlantUML 1.2025.2, Temurin Java 17.0.14+7, and Graphviz 12.2.1. The current comparison target is PlantUML 1.2026.9, Java 21.0.12.1+1, and Graphviz 14.0.1. Exact container digests and platform are locked in `scripts/toolchain.json` and `scripts/toolchain-current.json`; CI must run both targets. This is a tested pair of toolchains, not a claim that every intermediate or future version is supported.

The verification harness and detailed baseline evidence are repository resources, rather than archive runtime dependencies. Use Python 3.10+ and Docker from the checkout root. Initial toolchain preparation requires network access to pull the digest-pinned base and install native GD dependencies from the signed Ubuntu snapshot `20261017T000000Z`, using `scripts/Dockerfile`. Subsequent rendering runs with networking disabled. Both SVG and PNG use native Graphviz output; plugins are retained. These commands only prepare local evidence:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check.py --toolchain baseline
python3 scripts/check.py --toolchain current
python3 scripts/distribution.py --check --toolchain baseline
python3 scripts/distribution.py --check --toolchain current
```

Canonical diagrams use explicit `@startdot` / `@enddot` wrappers on both toolchains. Legacy `@startuml` is a compatibility case on the baseline renderer and an expected upstream rejection on current PlantUML. Current native DOT SVG rendering requires `PLANTUML_SECURITY_PROFILE=UNSECURE`; the harness applies that profile to trusted inputs inside offline, network-disabled containers.

The renderer gate covers published macro calls, Level 0–1 examples, all flow directions, optional IDs and titles, customization, repeated includes, multiple diagrams, escaping and line-break compatibility, permissive defaults, and expected validation failures. Require successful preprocessing, Graphviz execution, strict SVG parsing without error diagrams, and valid nonempty PNG output. Keep logs, expanded DOT, and render artifacts for both toolchains; inspect representative Level 0, Level 1, styling, and special-character diagrams visually.

After pushing the candidate branch, verify remote includes against its full commit SHA on both toolchains. Replace `FULL_COMMIT_SHA` with the candidate revision:

```sh
python3 scripts/check.py --toolchain baseline --remote-ref FULL_COMMIT_SHA
python3 scripts/check.py --toolchain current --remote-ref FULL_COMMIT_SHA
```

Remote verification needs network access. It mounts no local library files and must resolve the entry profile and core from the same commit-pinned `$DFD_ROOT`. Require green CI for the exact candidate SHA, including distribution checks. Rerun affected checks after any change; do not reuse an older commit's acceptance evidence.

## Distribution and provenance

The distribution command creates `build/dist/dfd-plantuml-<full-HEAD-sha>.zip` and a companion `SHA256SUMS`. It packages the three library files, license, user documentation, and examples under `dfd-plantuml/`. The internal `MANIFEST.json` records the source revision and per-file SHA256 values. No testing-repository dependency or build-only runtime is required to consume it.

Archive bytes come from the working tree and must match the candidate revision by default. First commit the intended changes and require a clean tree. The `--revision` option selects the full source SHA to compare against; it does not check out that revision or replace working-tree content. For development checks only, `--allow-dirty` permits uncommitted payload bytes and marks the manifest `source_state` as `working-tree`. A publishable candidate must have `source_state` equal to `committed`.

`--check` builds twice and compares bytes, checks the allowlist and file hashes, rejects unsafe archive paths and member types, and extracts into a fresh temporary directory. It renders every packaged example and the README installation snippet to SVG and PNG offline from that extracted tree. Distribution render results, toolchain metadata, logs, and outputs are retained under `build/dist/render/<toolchain>/`. A missing sibling core, accidental repository fallback, incomplete documentation dependency, or corrupt archive must fail the gate.

Verify the companion archive checksum from its directory:

```sh
cd build/dist
shasum -a 256 -c SHA256SUMS
```

Rebuilding an unchanged source tree with the same source revision must yield the same archive bytes. Retain both the archive and its checksum file as candidate artifacts. Checksums detect accidental corruption; they are not a signature or proof of publisher identity.

## Final review and later publication

Review the [Unreleased changelog](../CHANGELOG.md), [migration guide](MIGRATION.md), and [baseline provenance](https://github.com/ArmanAvanesyan/DFD-PlantUML/blob/main/docs/BASELINE.md). Confirm the supported API, remote installation requirement, line-break behavior, experimental exclusions, and renderer limitations are documented. Keep the existing historical `v0.1.0` tag unchanged: its library files are empty, so the usable pre-consolidation `main` commit is the compatibility reference.

Record the accepted candidate SHA, toolchain versions, check results, visual review, archive hash, and compatibility notes in the PR. Select the next version only after that review; Merge changes through review without automatic tagging or publication.

Only after separate authorization to publish should a maintainer choose the final release version, ensure the accepted source commit is on the official default branch, create its immutable tag, and publish the verified archive, checksums, and reviewed release notes. Any source change after acceptance requires a new candidate gate. This document deliberately provides no command that creates a tag or release.

## Proposed stdlib preparation

Bundled integration is currently proposed, not shipped. Before a future stdlib submission, require the deterministic export and actual candidate-JAR checks described in [stdlib status](STDLIB.md). Candidate evidence does not establish support in an official PlantUML release and does not authorize submission or publication.
