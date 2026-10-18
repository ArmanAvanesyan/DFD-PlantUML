# Migrating to the consolidated library

Use `ArmanAvanesyan/DFD-PlantUML` for supported Level 0 and Level 1 diagrams. `ArmanAvanesyan/test` remains an experimental repository; official diagrams must not depend on its files. This guide describes the unreleased consolidation and does not assign a release version.

## Install one matching set

For local use, place `DFD.puml`, `DFD_Level_0.puml`, and `DFD_Level_1.puml` from the same source commit in one directory. Include the desired profile; its sibling core loads without editing the library. Choose one profile per diagram.

For remote use, replace a direct profile URL with an explicit commit-pinned directory plus the profile include. Replace `COMMIT_SHA` with a full source commit that contains the consolidated library:

```plantuml
!$DFD_ROOT = "https://raw.githubusercontent.com/ArmanAvanesyan/DFD-PlantUML/COMMIT_SHA"
!includeurl $DFD_ROOT/DFD_Level_0.puml
```

Use `DFD_Level_1.puml` for Level 1. Both profile and core resolve through `$DFD_ROOT`; do not mix commits, repositories, or profiles. A mutable `main` URL can change without a diagram edit. No PlantUML standard-library registration is assumed.

## Use an explicit DOT wrapper

Use `@startdot` and `@enddot` around diagrams on both tested toolchains. PlantUML 1.2026.9 no longer infers DOT from the older `@startuml` wrapper; this upstream change requires updating that wrapper, even though the library macro signatures remain compatible. Legacy `@startuml` diagrams remain covered on the baseline PlantUML 1.2025.2 toolchain, and their rejection on 1.2026.9 is tested explicitly.

For trusted local DOT diagrams rendered to SVG with PlantUML 1.2026.9, set `PLANTUML_SECURITY_PROFILE=UNSECURE` (also called `INSECURE` upstream). Its default `LEGACY` profile suppresses native DOT SVG output. The repository harness configures this inside offline containers with networking disabled; remote verification uses an isolated mount without a local library fallback.

## Preserve existing calls

`startDfd(title)` and `endDfd()` still open and close the DOT graph. `startDfd()` now also accepts an empty title. The published level-specific process signatures remain distinct:

| Level | Call | Meaning |
|---|---|---|
| 0 | `Process(alias, label, id="0")` | Central process node |
| 1 | `Process(label)` | Open the process boundary |
| 1 | `SubProcess(alias, id, label)` | A process inside that boundary |
| 1 | `DataFlows()` | Close the boundary before external flows |

`External(alias, label, id="")`, `DataStore(alias, label, id="D")`, `Flow(from, to, label="")`, `Flow_Back(from, to, label="")`, and `BiFlow(from, to, label="")` retain their argument ordering and directions. `External_Entity` is an alias for `External`. Keep `DataFlows()` balanced with Level 1 `Process(label)`; malformed boundaries are errors.

The reference for compatibility is the previously usable official `main` commit `a09a92dc89b31b7e21f1c40b956714ff0789dabc`. The retained historical `v0.1.0` tag contains empty library files and cannot serve as a rendering baseline.

## Labels, customization, and validation

Single-backslash `\n` sequences retain the legacy meaning of a line break in node labels, flow labels, and titles. Use a doubled backslash (`\\n`) when literal backslash-plus-`n` text is intended. Actual line breaks are accepted too; construct one in a variable with `%chr(10)` and pass the variable to the macro. Other backslashes, including doubled UNC prefixes and trailing backslashes, remain literal. Only a run immediately before `n` uses the escape rule: each pair represents one literal backslash, and an unpaired backslash makes `n` a line break. Quotes, HTML and record punctuation, and Unicode are escaped as text. Aliases must remain simple DOT identifiers, such as `Customer` or `P1`; arbitrary DOT fragments are outside the public API.

Customization setters affect subsequent output. Set graph and title properties before `startDfd()`, and element/flow properties before their calls. Quote fractional dimensions, for example `SetProcessSize("2.5", "1.2")`. See the [API reference](API.md) for supported setters.

Validation stays off by default. Add `SetValidation(1)` before `startDfd()` to reject a second Level 0 process, Level 0 datastores, and flow endpoints that have not been declared. Endpoint matching is exact. This checks structure rather than complete DFD semantics. Registry and process count reset at `startDfd()`; style settings persist within a diagram.

## Experimental features

Do not migrate experimental `DFD_INIT`, `DFD_PROFILE_*`, or uniform `DFD_*` APIs by merely replacing the include URL. Rewrite those diagrams against the supported calls above. Level 2, alternate notations, cross-diagram balancing, automatic hierarchy linking, themes, and CLI generation remain outside the official library. Keep experiments in the testing repository.

Before upgrading a project, render its diagrams with a pinned supported toolchain, inspect representative outputs, and retain the old source pin until the results are accepted. See [release verification](RELEASING.md) for the candidate gate.
