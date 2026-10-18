# PlantUML stdlib status

**Proposed only.** Existing official PlantUML releases do not ship DFD-PlantUML. `<dfd/DFD_Level_0>` and `<dfd/DFD_Level_1>` are proposed bundled entrypoints, not working installation instructions for those releases. Use [local or commit-pinned remote installation](INSTALLATION.md) today.

## Planned export

Keep the root core and two profiles authoritative. A deterministic exporter is planned to read a committed revision and emit an explicit allowlist: the three library files, contribution metadata, and selected Level 0, Level 1, and customization examples under `_examples_`. Only include routing and documented license headers may differ; macro bodies and signatures must remain compatible.

Bundled profiles will resolve `<dfd/DFD>`. Bundled examples will resolve the corresponding profile. Exported files must have no network-dependent includes. A manifest outside the contribution directory will record source revision, source/export hashes, and each transformation. Preview metadata will use `unreleased` and a source commit permalink; those are candidate values for review, not an assigned release.

## Planned integration proof

An isolated candidate build must run the pinned stdlib encoder, copy the generated DFD resources and regenerated namespace index into a pinned PlantUML checkout, and build an actual JAR. Offline rendering must use that JAR without mounting the DFD source directory. Equivalent local and bundled fixtures must produce matching expanded DOT and semantic output. An unmodified official JAR is the negative control.

A passing candidate build proves local integration only. Later statuses are separate: accepted upstream, then shipped in a named official PlantUML release. Record the source commit, export hashes, encoder revision, engine revision, and shipping release independently; a directory name or metadata UID is not source provenance.

## Update and submission boundaries

Export and candidate-JAR tooling will be documented when implemented. No stdlib contribution is submitted by documentation or candidate checks. A future maintainer review must settle metadata/version values, inspect rendered evidence, authorize submission, and record the eventual shipped release. Tags and releases require separate authorization. See [release preparation](RELEASING.md).
