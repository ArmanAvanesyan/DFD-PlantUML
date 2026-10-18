# Compatibility and verification


Requires Python 3.10+ and Docker. Run `python3 scripts/check.py --toolchain baseline` and `python3 scripts/check.py --toolchain current` from a checkout. The tested targets are:

| Target | PlantUML | Java | Graphviz | Formats |
|---|---|---|---|---|
| Baseline | 1.2025.2 | Temurin 17.0.14+7 | 12.2.1 | SVG, native PNG |
| Current | 1.2026.9 | Temurin 21.0.12.1+1 | 14.0.1 | SVG, native PNG |

These are tested configurations, not a guarantee for every intermediate version. Both use `linux/amd64` (Docker emulation on ARM). Digest-pinned base images and dated, signed Ubuntu snapshot dependencies are locked under `scripts/toolchain*.json` and `scripts/Dockerfile`; `scripts/toolchain.py` builds the PNG-capable images once. Initial preparation needs network access. Offline rendering then uses `--network none`. The Graphviz wrapper suppresses warnings while retaining errors.

Use `@startdot` / `@enddot` on both targets. Legacy `@startuml` wrappers remain supported and tested on the baseline; PlantUML 1.2026.9 explicitly requires the DOT wrapper. For DOT SVG, the current engine also requires `PLANTUML_SECURITY_PROFILE=UNSECURE` (alias `INSECURE`) for trusted local diagrams. Our harness grants it only in isolated test containers, with networking disabled for offline checks. PNG is rendered natively through Graphviz GD, not converted from SVG.

After pushing a commit, run `python3 scripts/check.py --toolchain baseline --remote-ref FULL_COMMIT_SHA` and repeat with `--toolchain current` to render all documented examples through commit-pinned raw GitHub includes. Remote verification needs network access and mounts no local library files, ruling out accidental local fallback.

For migration details, see [migration guide](MIGRATION.md). To build and verify a candidate archive without publishing, run `python3 scripts/distribution.py --check --toolchain baseline`, then repeat with `--toolchain current`. The command verifies packaged bytes against the candidate revision; commit changes first. See [release preparation](RELEASING.md) for checksums, provenance, and the manual release gate.

Results, logs, expanded DOT, and SVGs are saved under `build/`. CI uploads them even on failure. Tests reject missing/malformed SVGs, error diagrams, preprocessing failures, and Graphviz failures; expected validation failures require the specific diagnostic. See [baseline investigation](https://github.com/ArmanAvanesyan/DFD-PlantUML/blob/main/docs/BASELINE.md) for original source hashes and render evidence.

## Supported and experimental features


Implemented: Level 0 and Level 1, published flow directions and macro signatures, optional titles/IDs, color/style/size/layout setters, safe text labels, optional structural validation, offline and remote includes, render CI.

Not part of this consolidation: Level 2, alternate notation selection, cross-diagram balancing, automatic hierarchy linking, themes, CLI generation, or standard-library registration. The experimental `DFD_INIT`, `DFD_PROFILE_*`, and uniform `DFD_*` APIs are not official interfaces. Retain experiments in `test` rather than treating their README claims as supported behavior.

Existing release/tag `v0.1.0` is retained unchanged. This consolidation assigns no new release number and performs no automatic publication. Contributions: [contribution guide](../CONTRIBUTING.md). License: [MIT](../LICENSE).
