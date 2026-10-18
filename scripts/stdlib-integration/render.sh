#!/bin/sh
set -eu
export GRAPHVIZ_DOT=/harness/dot.sh
exec java -jar /candidate.jar "$@"
