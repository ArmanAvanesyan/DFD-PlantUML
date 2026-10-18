# DFD-PlantUML

The official PlantUML library for Level 0 context diagrams and Level 1 data-flow diagrams. It generates Graphviz DOT through PlantUML macros. Experiments live in [ArmanAvanesyan/test](https://github.com/ArmanAvanesyan/test); official library files never import that repository.

## Installation

Download `DFD.puml`, `DFD_Level_0.puml`, and `DFD_Level_1.puml` from the same commit into one directory. Include the desired profile locally. No edits to its sibling include are needed. Choose one profile per diagram.

For a remote include, use `https://raw.githubusercontent.com/ArmanAvanesyan/DFD-PlantUML/COMMIT_SHA/DFD_Level_0.puml` (or Level 1), replacing `COMMIT_SHA` with the full commit you installed. Relative includes resolve to that same commit's core. Using `main` is convenient for experiments but follows future changes. No PlantUML standard-library installation is assumed.

## Examples

The following snippets are the executable files under `examples/`; their relative includes assume that directory layout. CI checks that these blocks remain identical to the files.

### Level 0

![Level 0](docs/rendered/level_0.svg)

```plantuml
@startuml
!include ../DFD_Level_0.puml
startDfd(Loan System)
External(Customer, "Customer")
Process(System, "Loan System")
Flow(Customer, System, "application")
Flow_Back(Customer, System, "decision")
BiFlow(Customer, System, "status")
endDfd()
@enduml
```

### Level 1

![Level 1](docs/rendered/level_1.svg)

```plantuml
@startuml
!include ../DFD_Level_1.puml
startDfd(Loan processing)
External(Customer, "Customer")
Process("Loan System")
SubProcess(Validate, "1.0", "Validate application")
SubProcess(Assess, "2.0", "Assess risk")
DataStore(Applications, "Applications")
DataFlows()
Flow(Customer, Validate, "application")
Flow(Validate, Assess, "validated data")
BiFlow(Assess, Applications, "assessment")
Flow_Back(Customer, Assess, "decision")
endDfd()
@enduml
```

`Process(label)` opens the Level 1 boundary; `DataFlows()` closes it before the external flows. Level 0 instead uses `Process(alias, label, id="0")` to create its central node. Existing published call signatures are retained.

## API and customization

| Call | Behavior |
|---|---|
| `startDfd(title="")`, `endDfd()` | Open/close a graph; reset node registry and process count |
| `External(alias, label, id="")` | External entity; `External_Entity` is an alias |
| `Process(alias, label, id="0")` | Level 0 process |
| `Process(label)`, `DataFlows()` | Open/close a Level 1 process boundary |
| `SubProcess(alias, id, label)` | Level 1 process node; argument order is unchanged |
| `DataStore(alias, label, id="D")` | Data store (Level 0 allowed only when validation is off) |
| `Flow(from, to, label="")` | Forward arrow |
| `Flow_Back(from, to, label="")` | Arrow from `to` toward `from` |
| `BiFlow(from, to, label="")` | Two arrowheads |
| `SetValidation(1)` | Opt into Level 0 restrictions and exact endpoint validation |

Aliases must be simple DOT identifiers, such as `Customer` or `P1`; labels are arbitrary text. Quotes, backslashes, record punctuation, Unicode, and actual line breaks are escaped by the renderer. Construct a line break with `%chr(10)` in a variable, then pass that variable to the macro; unquoted macros do not accept inline expressions. Untrusted aliases and raw DOT fragments are outside the API.

Customization setters apply to subsequent output. Call them before `startDfd()` for graph/title settings, and before creating the affected elements/flows. Quote fractional numbers, e.g. `SetProcessSize("2.5", "1.2")`, because the pinned PlantUML preprocessor does not preserve unquoted decimal literals reliably.

- Titles: `SetTitleFontSize`, `SetTitleFontColor`, `SetSubtitleFontSize`, `SetSubtitleFontColor`.
- Elements: `SetComponentFontSize`, `SetComponentFontColor`, `SetComponentBorderColor`; `SetExternalStyle/FillColor/Shape/Size`, `SetProcessStyle/FillColor/Shape/Size`, `SetDataStoreStyle/FillColor/Shape/Size`.
- Batches: `SetAllComponentColors(fill, border="grey", font="#000000")`, `SetAllComponentStyles(style="filled")`, `SetAllComponentSizes(width=2, height=1)`.
- Flows: `SetFlowStyle`, `SetFlowColor`, `SetFlowFontColor`, `SetFlowFontSize`, `SetFlowPenWidth`, `SetAllFlowProperties(style="solid", color="black", fontColor="black", fontSize=13, penWidth=1)`.
- Layout: `SetRankDir`, `SetRankSep`, `SetNodeSep`, `SetSplines`, `SetFlowConcentrate`.

A complete customization example:

```plantuml
@startuml
!include ../DFD_Level_0.puml
SetTitleFontColor("#234567")
SetSubtitleFontColor("#345678")
SetExternalFillColor("#FFFDE7")
SetProcessFillColor("#E3F2FD")
SetProcessSize("2.5", "1.2")
SetComponentFontSize(14)
SetAllFlowProperties("dashed", "#BB2222", "#234567", 12, 2)
SetRankDir("TB")
SetRankSep("1.2")
SetSplines("polyline")
SetValidation(1)
startDfd(Customized diagram)
External(User, "Customer")
Process(System, "Loan System", "0")
Flow(User, System, "request")
BiFlow(System, User)
endDfd()
@enduml
```

Validation is off by default to retain permissive published behavior. When enabled, Level 0 rejects a second process and datastores; all flow endpoints must already have been declared. This is structural checking, not full DFD semantic analysis. State resets for each `startDfd()`; style settings persist within the same diagram. Misbalanced Level 1 boundaries are always errors.

## Verification

Requires Python 3.10+ and Docker. Run `python3 scripts/check.py` from a checkout. The first run downloads the digest-pinned image in `scripts/toolchain.json`; subsequent runs render with `--network none`. The image pins Java 17.0.14+7, PlantUML 1.2025.2, and Graphviz 12.2.1 on linux/amd64, including on ARM hosts through Docker emulation. The harness removes the upstream image's unusable GD plugin in each transient container and suppresses Graphviz warnings with `-q`; Graphviz errors remain visible. This prevents warnings from being merged into SVG bytes.

After pushing a commit, run `python3 scripts/check.py --remote-ref FULL_COMMIT_SHA` to render every documented example through commit-pinned raw GitHub includes. This mode needs network access. It verifies sibling remote resolution rather than downloading files and pretending they were remote includes.

Results, logs, expanded DOT, and SVGs are saved under `build/`. CI uploads them even on failure. Tests reject missing/malformed SVGs, error diagrams, preprocessing failures, and Graphviz failures; expected validation failures require the specific diagnostic. See [baseline investigation](docs/BASELINE.md) for original source hashes and render evidence.

## Compatibility and status

Implemented: Level 0 and Level 1, published flow directions and macro signatures, optional titles/IDs, color/style/size/layout setters, safe text labels, optional structural validation, offline and remote includes, render CI.

Not part of this consolidation: Level 2, alternate notation selection, cross-diagram balancing, automatic hierarchy linking, themes, CLI generation, or standard-library registration. The experimental `DFD_INIT`, `DFD_PROFILE_*`, and uniform `DFD_*` APIs are not official interfaces. Retain experiments in `test` rather than treating their README claims as supported behavior.

Existing release/tag `v0.1.0` is retained unchanged. This consolidation assigns no new release number and performs no automatic publication. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). License: [MIT](LICENSE).
