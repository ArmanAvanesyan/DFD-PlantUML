#!/bin/sh
set -eu
# libgd and its signed snapshot dependencies are installed by scripts/Dockerfile.
# Keep native PNG support; the wrapper suppresses warnings but retains errors.
export GRAPHVIZ_DOT="$(dirname "$0")/dot.sh"
exec java -jar /opt/plantuml.jar "$@"
