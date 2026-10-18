# Verified consolidation baseline

Baseline investigation on 2026-10-18 rendered 28 cases using unchanged source candidates or explicitly localized include chains: **9 semantic passes and 19 failures**. No fully working newer local library was established. FamilyA with its matching local core verifies the published Level 0–1 contract; the original `test.md` examples fail against current testing dependencies.

## Candidates and decisions

| Candidate | Actual include chain | Matching local replay | Decision |
|---|---|---|---|
| Official main | Level 0 and 1 pass | Level 0 and 1 pass | Published compatibility reference |
| FamilyA | Level 0 and 1 fail; imports current testing core | Level 0 and 1 pass | Verified coherent local implementation of published API |
| Official develop | Both levels fail | Level 0 passes; Level 1 fails | Selectively repair customization; do not copy wholesale |
| Root lab | Both levels fail | Not a complete coherent library: missing bootstrap modules and mismatched profile dependencies | Preserve experimental source |
| plantuml-dfd | Both levels fail | Not repaired for baseline | Preserve experimental design material |
| notation_experiments | Two standalone demonstrations pass | Not applicable | Exclude incompatible notation/API experiments |
| test/main | Both levels fail | Both levels fail | Experiments only |
| Original test.md | Both blocks fail | Both blocks fail | Historical invocation is evidence, not a current passing baseline |

The 28 cases include 16 actual/local candidate cases across FamilyA, root, plantuml-dfd, official main, and test/main; four develop cases; two standalone notation cases; and six test.md cases. Three official feature branches have byte-identical library files to develop. Their repository-support files require separate selective review.

## Provenance and replay

[remote-manifest.json](evidence/remote-manifest.json) records exact commits and SHA256 hashes of all original official/testing library files. [source-manifest.json](evidence/source-manifest.json) records original local source paths and hashes before localization. Snapshot paths refer to the investigation machine; copies and hashes identify evidence independently of those paths.

Localization changes only the core include from its original remote URL to a matching sibling `DFD.puml`; it does not repair library bodies. FamilyA’s original profiles import `test/main`, whereas its matching local core follows the published contract. Official main is commit `a09a92dc89b31b7e21f1c40b956714ff0789dabc`, develop is `f83acc34dbcafcae1545dc2527ae06df5cc5f41b`, and test/main is `4f6f30fbdd060db74864b24e9ecc5829e11f3b30`.

The `test-md-*-pinned` cases pin the entry profile URL, whose unchanged contents still transitively import mutable test/main core. The `test-md-*-local` cases provide the fully matching local replay of the recorded testing commit. Actual remote renders record behavior observed during this investigation; their URLs remain mutable.

The existing `v0.1.0` tag identifies `baa344fe1ec1b4a20486a47f06796183f1ccf16e`. This work assigns no release version and does not change existing branches or experiments. Repairs introduced in the consolidated library are new implementation work, distinct from the original candidates verified here.

## Toolchain and diagnostics

The pinned Docker image is `plantuml/plantuml@sha256:62c11f4cec2c430a435df8b2892f9b1a7654393c8ef2086faaca32cc16151370`: PlantUML 1.2025.2, Temurin Java 17.0.14+7, and Graphviz 12.2.1. [toolchain.log](evidence/toolchain.log) preserves measured version output, including the nonfatal Graphviz plugin warning. Remote includes used `PLANTUML_SECURITY_PROFILE=UNSECURE`.

Run a retained coherent baseline example from the repository root (its matching localized sources are included):

```sh
docker run --rm --entrypoint java \
  -e PLANTUML_SECURITY_PROFILE=UNSECURE \
  -v "$PWD:/work" \
  plantuml/plantuml@sha256:62c11f4cec2c430a435df8b2892f9b1a7654393c8ef2086faaca32cc16151370 \
  -jar /opt/plantuml.jar -tsvg -failfast2 /work/docs/evidence/familyA-L0-local/case.puml
```

[result details](evidence/results.json) retain each baseline command, original exit status, semantic classification, raw XML classification, and normalization details. Commands contain the original temporary mount and case paths. Selected inputs, preprocessed output, logs, and SVGs are retained beside this report. Failed cases were rerendered without `-failfast2` to retain diagnostic artifacts; their initial statuses remain unchanged.

- The no-title test.md block fails with `Function not found startDfd`.
- The titled block and testing-core examples fail with a sequence-syntax error at emitted `digraph dfd {` under this pinned runtime.
- Develop Level 1 reports a fatal parsing error around its malformed datastore procedure.
- Root Level 0 and other malformed DOT cases can return exit 0 while writing plain-text Graphviz diagnostics to a file named `.svg`.

The original pinned runtime emits a missing-GD-plugin warning before XML on otherwise successful renderings. Consequently, the nine semantic passes do **not** establish strict acceptance of the original raw SVG artifacts. Retained positive files preserve those original bytes as `case.raw-svg`; `case.svg` removes only the known leading warning before the XML/SVG root. [normalization.json](evidence/normalization.json) records the removed prefixes and both hashes. The normalized SVGs are display artifacts, not unmodified renderer outputs. Replaying the command above reproduces the original warning behavior unless the runtime warning is addressed.

The consolidated runtime separately removes the broken GD plugin and suppresses normal Graphviz chatter while retaining errors. Its final strict checks are independent of this baseline. Acceptance requires a successful process status, valid XML with an SVG root, and rejection of PlantUML error diagrams. Baseline failures do not claim these examples never rendered under another historical runtime. The consolidated implementation must independently pass compatibility, escaping, customization, validation, and offline tests.

## Retained render evidence

| Example | Artifact |
|---|---|
| Official main Level 0 | [SVG](evidence/official-main-L0-local/case.svg) |
| Official main Level 1 | [SVG](evidence/official-main-L1-local/case.svg) |
| Coherent FamilyA Level 0 | [SVG](evidence/familyA-L0-local/case.svg) |
| Coherent FamilyA Level 1 | [SVG](evidence/familyA-L1-local/case.svg) |
| Develop Level 0 with matching core | [SVG](evidence/develop-L0-local/case.svg) |
| Original test.md no-title error | [diagnostic SVG](evidence/test-md-1-local/case.svg) |
| Original test.md titled error | [diagnostic SVG](evidence/test-md-2-local/case.svg) |

[evidence/SHA256SUMS](evidence/SHA256SUMS) covers every retained evidence file except itself. [report.md](evidence/report.md) preserves the complete case matrix. The original local lab is untouched.

## Consolidation decisions

The official main/FamilyA contract supplies the public API and original default shapes. The consolidated implementation repairs sibling include resolution, optional titles and IDs, DOT/HTML/record escaping, active customization variables, exact alias registration, and opt-in structural assertions. These are new repairs, not claims about the original source. The original working coherent FamilyA files remain retained in the evidence directory.

Contribution guidance and bug/feature forms were adapted selectively. The old labeling, stale closure, and automated-release workflows were not imported: they do not verify diagrams, assume repository configuration/permissions, and publication remains manual. A dedicated read-only render workflow replaces that gap.

`docs/rendered/` contains the consolidated examples and the 23-check offline result. These artifacts were produced by the repaired runtime wrapper with network disabled and parsed strictly without normalizing SVG bytes. Representative Level 0, Level 1, customization, and special-character renders were visually inspected. The baseline evidence above remains an independent record of original candidate behavior.

Remote include integration exposed a runtime limitation: PlantUML 1.2025.2 resolves relative includes as local files, even when the including profile was fetched by URL. Official remote examples therefore set `$DFD_ROOT` to one commit-pinned directory; both profile and core use that directory. Local profiles retain ordinary sibling includes. Remote checks mount only generated example inputs and the rendering harness, never a local core, so fallback cannot mask errors. This explicit remote base is a verified adaptation of the planned sibling-resolution behavior.
