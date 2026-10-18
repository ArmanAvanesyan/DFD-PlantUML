# PlantUML stdlib status

**Proposed only.** Existing official PlantUML releases do not ship DFD-PlantUML. `<dfd/DFD_Level_0>` and `<dfd/DFD_Level_1>` are proposed bundled entrypoints, not working installation instructions for those releases. Use [local or commit-pinned remote installation](INSTALLATION.md) today.

## Reproducible preview export

The root core and two profiles remain authoritative. The exporter reads Git objects from a committed revision and emits an explicit allowlist: the three library files, contribution metadata, and Level 0, Level 1, and customization examples under `_examples_`. It ignores uncommitted source edits. Only include routing and committed MIT license comments differ; macro bodies and signatures are preserved.

```sh
python3 scripts/stdlib.py export --revision HEAD --output build/stdlib
python3 scripts/stdlib.py check --revision HEAD --output build/stdlib
```

`build/stdlib/dfd/` is the generated contribution directory; the adjacent `MANIFEST.json` records the source commit, input/output hashes, and exact transformations. The check reconstructs the expected committed export, verifies reproducibility, and compares every output byte and path. Export/check reject unexpected or stale contents rather than deleting files. After changing the source revision, choose a new empty output directory (for example `build/stdlib-next`) or explicitly remove only your previous generated export before rerunning. Identical exports can be repeated in place.

Bundled profiles resolve `<dfd/DFD>` and examples resolve the corresponding profile. The only allowed exported includes target the three DFD bundled files; local and remote fallbacks are rejected. The current encoder's raw GitHub URL restriction is checked before packaging. Source filenames and local/remote includes outside this derived export are unchanged.

Preview metadata uses `version: unreleased` and a source commit permalink as `release`. These are candidate review values, not a release number or published release. The metadata template is maintained upstream; generated files are ignored and must not be edited manually. The manifest remains outside the contribution so it cannot become an unintended bundled resource.

## Planned integration proof

An isolated candidate build must run the pinned stdlib encoder, copy the generated DFD resources and regenerated namespace index into a pinned PlantUML checkout, and build an actual JAR. Offline rendering must use that JAR without mounting the DFD source directory. Equivalent local and bundled fixtures must produce matching expanded DOT and semantic output. An unmodified official JAR is the negative control.

A passing candidate build proves local integration only. Later statuses are separate: accepted upstream, then shipped in a named official PlantUML release. Record the source commit, export hashes, encoder revision, engine revision, and shipping release independently; a directory name or metadata UID is not source provenance.

## Update and submission boundaries

The exporter prepares files only; actual-JAR integration is the separate planned gate above. No stdlib contribution is submitted by exporting or checking. A future maintainer review must settle metadata/version values, inspect rendered evidence, authorize submission, and record the eventual shipped release. Tags and releases require separate authorization. See [release preparation](RELEASING.md).
