# PlantUML stdlib status

**Local candidate integration only; not shipped.** Existing official PlantUML releases do not ship DFD-PlantUML. `<dfd/DFD_Level_0>` and `<dfd/DFD_Level_1>` are candidate bundled entrypoints, not working installation instructions for those official releases. Use [local or commit-pinned remote installation](INSTALLATION.md) today.

## Reproducible preview export

The root core and two profiles remain authoritative. The exporter reads Git objects from a committed revision and emits an explicit allowlist: the three library files, contribution metadata, and Level 0, Level 1, and customization examples under `_examples_`. It ignores uncommitted source edits. Only include routing and committed MIT license comments differ; macro bodies and signatures are preserved.

```sh
python3 scripts/stdlib.py export --revision HEAD --output build/stdlib
python3 scripts/stdlib.py check --revision HEAD --output build/stdlib
```

`build/stdlib/dfd/` is the generated contribution directory; the adjacent `MANIFEST.json` records the source commit, input/output hashes, and exact transformations. The check reconstructs the expected committed export, verifies reproducibility, and compares every output byte and path. Export/check reject unexpected or stale contents rather than deleting files. After changing the source revision, choose a new empty output directory (for example `build/stdlib-next`) or explicitly remove only your previous generated export before rerunning. Identical exports can be repeated in place.

Bundled profiles resolve `<dfd/DFD>` and examples resolve the corresponding profile. The only allowed exported includes target the three DFD bundled files; local and remote fallbacks are rejected. The current encoder's raw GitHub URL restriction is checked before packaging. Source filenames and local/remote includes outside this derived export are unchanged.

Preview metadata uses `version: unreleased` and a source commit permalink as `release`. These are candidate review values, not a release number or published release. The metadata template is maintained upstream; generated files are ignored and must not be edited manually. The manifest remains outside the contribution so it cannot become an unintended bundled resource.

## Actual candidate-JAR integration

Requires Python 3.10+, Git, Docker, and network access for initial source/toolchain/Gradle dependency retrieval. From a checkout run:

```sh
python3 -u scripts/stdlib_integration.py --revision HEAD
```

The integration lock pins stdlib encoder `d4a391be62499063d967348b975e5e6407db77a5`, PlantUML `18d0aae311a4f1eb3723bb4b0ad939185e22f166`, and an immutable Temurin JDK image matching the current renderer's Java patch. The build-only layer adds compiler tools; rendering still uses the existing digest-pinned current Java/Graphviz runtime. Upstream Gradle wrappers run the Java encoder (`runSpm`) and actual GPL JAR build (`jar -Pfast`); unrelated browser/TeaVM outputs are outside this gate.

Sources are fetched into disposable checkouts below `build/stdlib-integration/`. The full catalog is encoded to regenerate a genuine namespace index. Only DFD resources and `home.spm` are copied into the pinned PlantUML checkout. The harness verifies packaged resource bytes and the exact namespace entry inside the built JAR. It does not use an include-path overlay as a substitute for packaging.

Bundled rendering mounts only its fixtures, the candidate JAR, and harness scripts, with networking disabled and no local DFD library files. Local counterparts use the same candidate engine with the committed canonical files. The gate compares expanded DOT and semantic SVG contents, including multiple-diagram outputs; checks expected validation failures; and renders all documented examples to SVG and native PNG. An unmodified official JAR must fail specifically because the DFD include is absent. A suppression SVG or an unrelated failure does not satisfy this control.

Evidence includes `candidate.jar`, `build-provenance.json`, full build logs, staged fixtures, expanded DOT, SVG/PNG, expected diagnostics, and artifact hashes. The `Candidate stdlib integration` workflow runs on PRs and manual dispatch, with read-only repository permissions, content-keyed dependency caches, and evidence retained on failure. It never submits or publishes anything.

To rerun validation without rebuilding, use the exact source revision recorded in the existing provenance:

```sh
python3 -u scripts/stdlib_integration.py --revision FULL_SOURCE_SHA --validate-only
```

A new source revision requires a new empty output directory, for example `--output build/stdlib-integration-next`; stale exported content is rejected. Generated checkouts may be recreated inside that selected build directory. The baseline engine remains covered for local/remote compatibility; this candidate gate targets the current SPM-based engine and does not retrofit SPM resources into the baseline's older packaging format.

A passing candidate build proves local integration only. Later statuses are separate: accepted upstream, then shipped in a named official PlantUML release. Record the source commit, export hashes, encoder revision, engine revision, and shipping release independently; a directory name or metadata UID is not source provenance.

## Update and submission boundaries

No stdlib contribution is submitted by exporting or checking the candidate JAR. A future maintainer review must settle metadata/version values, inspect rendered evidence, authorize submission, and record the eventual shipped release. Tags and releases require separate authorization. See [release preparation](RELEASING.md).
