#!/bin/sh
set -eu
# The upstream image advertises a GD plugin without shipping libgd.so.3.
# SVG uses the core plugin. Remove the unusable plugin and rebuild only the
# container's transient plugin cache so warnings cannot corrupt SVG stdout.
rm -f /usr/local/lib/graphviz/libgvplugin_gd.*
rm -f /usr/local/lib/graphviz/config6
dot -c
export GRAPHVIZ_DOT="$(dirname "$0")/dot.sh"
exec java -jar /opt/plantuml.jar "$@"
