#!/bin/sh
# Suppress warnings (including upstream non-ASCII width warnings) while retaining
# Graphviz errors and status. PlantUML otherwise merges warnings into SVG bytes.
exec dot -q "$@"
