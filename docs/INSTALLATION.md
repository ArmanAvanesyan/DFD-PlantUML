# Installation


Download `DFD.puml`, `DFD_Level_0.puml`, and `DFD_Level_1.puml` from the same commit into one directory. Include the desired profile locally. No edits to its sibling include are needed. Choose one profile per diagram.

For remote use, set `$DFD_ROOT` to the directory of one full source commit, then include its profile (replace `COMMIT_SHA`):

```text
@startdot
!$DFD_ROOT = "https://raw.githubusercontent.com/ArmanAvanesyan/DFD-PlantUML/COMMIT_SHA"
!includeurl $DFD_ROOT/DFD_Level_0.puml
startDfd()
External(User, "Customer")
Process(System, "Loan System")
Flow(User, System)
endDfd()
@enddot
```

Use `DFD_Level_1.puml` for Level 1. The profile loads `$DFD_ROOT/DFD.puml`, ensuring it uses the same commit. The pinned PlantUML engine does not infer a sibling URL from a remote include, so this explicit directory is required; local installs use sibling includes without configuration. Using `main` follows future changes. Bundled `<dfd/...>` installation is proposed only. Existing official PlantUML releases do not contain this library. See [stdlib status](STDLIB.md).


The [README examples](../README.md#examples) use local includes relative to the packaged `examples/` directory. For renderer prerequisites and trusted SVG permissions, see [compatibility](COMPATIBILITY.md).
