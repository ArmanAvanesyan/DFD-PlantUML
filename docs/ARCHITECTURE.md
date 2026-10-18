# Library architecture

The three root `.puml` files are the canonical implementation and stable public distribution paths. There is no generated-source layer. `DFD.puml` owns shared rendering, text escaping, configuration, node registration, flows, and graph lifecycle. `DFD_Level_0.puml` defines the central process and datastore rules; `DFD_Level_1.puml` defines the process boundary, subprocesses, and datastores.

## Includes and initialization

Profiles first resolve the matching core: through `$DFD_ROOT/DFD.puml` when callers set that directory, otherwise through the local sibling `DFD.puml`. Remote users must pin a single source commit explicitly; the baseline preprocessor does not infer a remote sibling directory. Core and profile guards prevent repeated initialization. Select one profile per diagram; their `Process` definitions intentionally differ.

The shared core initializes styling and validation defaults once. `startDfd()` resets node registration, process count, and open-boundary state and emits DOT graph properties. A Level 1 `Process(label)` opens a cluster, `DataFlows()` closes it, and `endDfd()` closes the graph. Boundary misuse raises preprocessing assertions. Styles and validation are not reset by `startDfd()`.

## Rendering and text

Public macros emit Graphviz DOT, not PlantUML UML nodes. PlantUML preprocesses the calls; Graphviz performs layout and native SVG/PNG rendering. Use explicit DOT wrappers and the renderer/security configuration described in [compatibility](COMPATIBILITY.md).

Text helpers normalize legacy line breaks and escape DOT strings, record labels, or HTML labels according to their output context. Node aliases are simple DOT identifiers supplied by the caller. Raw DOT fragments and arbitrary aliases are outside the safe text API. With validation enabled, a delimiter-bounded registry provides exact alias matching; validation remains permissive by default.

Setters update the variables consumed when each graph, element, or flow is emitted. They are not retroactive. [API](API.md) describes their call order and defaults; [migration](MIGRATION.md) records compatibility constraints.

## Distribution boundaries

The archive packages canonical files, user documentation, and executable examples. Tests, toolchain builders, and experimental code are not runtime dependencies. The proposed stdlib export is a separate derived distribution: it may change include routing for bundled resources while keeping macro bodies and public signatures intact. It must carry explicit source provenance and must never become a manually maintained second implementation. See [stdlib status](STDLIB.md).
