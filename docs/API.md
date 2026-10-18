# Public API and customization

Include exactly one level profile before calling the API. Its core implementation is shared; profile-specific `Process` signatures are intentionally different.


| Call | Behavior |
|---|---|
| `startDfd(title="")`, `endDfd()` | Open/close a graph; start resets node registry and process count |
| `External(alias, label, id="")` | External entity; `External_Entity` is an alias |
| `Process(alias, label, id="0")` | Level 0 process |
| `Process(label)`, `DataFlows()` | Open/close a Level 1 process boundary |
| `SubProcess(alias, id, label)` | Level 1 process node; argument order is unchanged |
| `DataStore(alias, label, id="D")` | Data store (Level 0 allowed only when validation is off) |
| `Flow(from, to, label="")` | Forward arrow |
| `Flow_Back(from, to, label="")` | Arrow from `to` toward `from` |
| `BiFlow(from, to, label="")` | Two arrowheads |
| `SetValidation(enabled=1)` | Opt into Level 0 restrictions and exact endpoint validation |

Aliases must be simple DOT identifiers, such as `Customer` or `P1`; labels are text. Quotes, backslashes, record punctuation, Unicode, and actual line breaks are escaped by the renderer. Single-backslash `\n` retains its legacy line-break meaning; use doubled backslashes (`\\n`) for literal backslash-plus-`n` text. Other backslashes remain literal. You can also construct a line break with `%chr(10)` in a variable, then pass that variable to the macro; unquoted macros do not accept inline expressions. Untrusted aliases and raw DOT fragments are outside the API.

Customization setters apply to subsequent output. Call them before `startDfd()` for graph/title settings, and before creating the affected elements/flows. Quote fractional numbers, e.g. `SetProcessSize("2.5", "1.2")`, because the pinned PlantUML preprocessor does not preserve unquoted decimal literals reliably.

- Titles: `SetTitleFontSize`, `SetTitleFontColor`, `SetSubtitleFontSize`, `SetSubtitleFontColor`.
- Elements: `SetComponentFontSize`, `SetComponentFontColor`, `SetComponentBorderColor`; `SetExternalStyle/FillColor/Shape/Size`, `SetProcessStyle/FillColor/Shape/Size`, `SetDataStoreStyle/FillColor/Shape/Size`.
- Batches: `SetAllComponentColors(fill, border="grey", font="#000000")`, `SetAllComponentStyles(style="filled")`, `SetAllComponentSizes(width=2, height=1)`.
- Flows: `SetFlowStyle`, `SetFlowColor`, `SetFlowFontColor`, `SetFlowFontSize`, `SetFlowPenWidth`, `SetAllFlowProperties(style="solid", color="black", fontColor="black", fontSize=13, penWidth=1)`.
- Layout: `SetRankDir`, `SetRankSep`, `SetNodeSep`, `SetSplines`, `SetFlowConcentrate`.


Every single-property setter above takes one required `value`. `SetExternalSize(width=2, height=1)`, `SetProcessSize(width=2, height=1)`, and `SetDataStoreSize(width=2, height=1)` accept two optional dimensions. These setter argument defaults differ from some initial dimensions below.

### Initial rendering defaults

| Property | Initial value |
|---|---|
| Title / subtitle | size 16 / 10; both black |
| Component text / border | size 12, `#000000` / `grey` |
| External | `box`, `lightsteelblue1`, `filled`, width 1, height 2 |
| Process | `Mrecord`, `lightsteelblue1`, `filled`, width 2, height 0 |
| Datastore | `record`, `lightsteelblue1`, `filled`, width 2, height 0 |
| Flow | solid, black, black text size 13, pen width 1 |
| Layout | rank direction `LR`, rank separation `1.5`, node separation `0.5`, splines `spline`, concentration `false` |

Shape, color, style, spline, and layout values are Graphviz values passed through to DOT. The library does not independently validate all Graphviz settings.


## Additional graph and flow helpers

`Title(title)` emits a graph title using the current title and subtitle settings. Normally pass the title to `startDfd(title)` instead. `Flow_(from, to, label="", direction="forward")` is the shared flow helper; the named flow calls select `forward`, `back`, or `both`. Prefer those named calls for ordinary diagrams. `DFD_*` helpers and internal global variables are implementation details.

## Validation and state

Validation is off by default to retain permissive published behavior. `SetValidation(1)` opts into rejecting a second Level 0 process, Level 0 datastores, and undeclared flow endpoints. `SetValidation(0)` disables those checks. Endpoint matching is exact. This is structural checking, not full DFD semantic analysis. Misbalanced Level 1 boundaries are always errors. Close a Level 1 boundary with `DataFlows()` before `endDfd()`.

`startDfd()` resets the node registry, process count, and boundary state. It does not reset customization or the validation setting. Repeated includes are guarded; use one profile per diagram. A separate diagram has its own preprocessing context.

See the executable [customization example](../examples/customization.puml), [migration guide](MIGRATION.md), and [renderer compatibility](COMPATIBILITY.md).
