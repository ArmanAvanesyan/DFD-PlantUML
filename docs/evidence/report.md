# Baseline render evidence

Pinned image: `plantuml/plantuml@sha256:62c11f4cec2c430a435df8b2892f9b1a7654393c8ef2086faaca32cc16151370`. See toolchain.log for measured runtime.

28 cases render original candidates. The 9 PASS classifications below describe semantic rendering outcomes, not strict acceptance of the raw SVG bytes: otherwise successful raw files contain a leading Graphviz missing-GD-plugin warning. Selected retained SVGs are explicitly normalized for display; original bytes are retained as case.raw-svg and normalization.json records the transformation. Localized cases modify only remote core includes to sibling includes; original source SHA256 recorded before rewriting. No library repairs were made. Diagnostics rerender failed cases without failfast2 to retain error output; initial status remains in status.json.

`test-md-*-pinned` pins the profile URL only: that original profile still transitively imports mutable test/main core. `test-md-*-local` is the fully matching local replay of commit 4f6f30fbdd060db74864b24e9ecc5829e11f3b30.

| Case | Result | Initial exit | Diagnostic |
|---|---|---:|---|
| familyA-L0-actual | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| familyA-L0-local | PASS | 0 |  |
| familyA-L1-actual | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| familyA-L1-local | PASS | 0 |  |
| root-L0-actual | FAIL | 0 | Warning: Could not load "/usr/local/lib/graphviz/libgvplugin_gd.so.6" - It was found, so perhaps one of its dependents was not.  Try ldd. Error: <stdin>: syntax error in line 4 near '('  |
| root-L1-actual | FAIL | 200 | Process("Loan System")  /  Function not found Process |
| plantuml-dfd-L0-actual | FAIL | 0 | Warning: Could not load "/usr/local/lib/graphviz/libgvplugin_gd.so.6" - It was found, so perhaps one of its dependents was not.  Try ldd. Error: <stdin>: syntax error in line 14 near '='  |
| plantuml-dfd-L1-actual | FAIL | 200 | Process("Loan System")  /  Function not found Process |
| official-main-L0-actual | PASS | 0 |  |
| official-main-L0-local | PASS | 0 |  |
| official-main-L1-actual | PASS | 0 |  |
| official-main-L1-local | PASS | 0 |  |
| test-main-L0-actual | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| test-main-L0-local | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| test-main-L1-actual | FAIL | 200 | SetProcessFillColor("#E3F2FD")     ' Light blue for processes  /  Syntax Error? (Assumed diagram type: state) |
| test-main-L1-local | FAIL | 200 | SetProcessFillColor("#E3F2FD")     ' Light blue for processes  /  Syntax Error? (Assumed diagram type: state) |
| develop-L0-actual | FAIL | 0 | Warning: Could not load "/usr/local/lib/graphviz/libgvplugin_gd.so.6" - It was found, so perhaps one of its dependents was not.  Try ldd. Error: <stdin>: syntax error in line 4 near '('  |
| develop-L0-local | PASS | 0 |  |
| develop-L1-actual | FAIL | 200 | Process("Loan System")  /  Function not found Process |
| develop-L1-local | FAIL | 200 | Component($alias, $label, $id, $DATASTORE_SHAPE $DATASTORE_FILLCOLOR, $DATASTORE_WIDTH, $DATASTORE_HEIGHT, "datastot ...  /  Fatal parsing error |
| notation-L0-standalone | PASS | 0 |  |
| notation-L1-standalone | PASS | 0 |  |
| test-md-1-actual | FAIL | 200 | startDfd()  /  Function not found startDfd |
| test-md-1-pinned | FAIL | 200 | startDfd()  /  Function not found startDfd |
| test-md-1-local | FAIL | 200 | startDfd()  /  Function not found startDfd |
| test-md-2-actual | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| test-md-2-pinned | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |
| test-md-2-local | FAIL | 200 | digraph dfd {  /  Syntax Error? (Assumed diagram type: sequence) |

## Baseline decision

Official main and coherent FamilyA Level 0/1 render with published API. FamilyA actual remote dependency fails, proving source location alone does not identify executed implementation. Official main is a verified compatibility reference; coherent FamilyA is a verified local equivalent. Develop Level 0 becomes renderable by correcting only core include provenance, making it a candidate for selective customization repair. Develop Level 1 remains syntactically broken. Root and plantuml-dfd remain incomplete. Standalone notation examples render, but are not compatible entrypoint libraries; their literal aliases and argument-order differences exclude promotion.

Actual test.md no-title block fails with `Function not found startDfd`; titled block and test core examples fail with `Syntax Error? (Assumed diagram type: sequence)` at emitted `digraph dfd {`. These outcomes are specific to the pinned runtime, not claims about historical runtime behavior.

Some Graphviz failures return process exit 0 and write diagnostic plain text to files named .svg. Acceptance requires exit status, XML parsing, an SVG root, and rejection of error diagrams.

Remote includes were rendered with PLANTUML_SECURITY_PROFILE=UNSECURE. Network-disabled acceptance belongs to the consolidated test suite; these baseline originals intentionally include remote code.
