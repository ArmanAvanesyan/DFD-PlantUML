#!/bin/sh
# Run unchanged upstream builds on Linux storage. In particular, upstream's
# unbuffered sprite writer must not issue each byte across a macOS bind mount.
set -eu
export GRADLE_USER_HOME=/gradle
export JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=2 -Xmx3g'
project="$1"
shift
case "$project" in stdlib|plantuml) ;; *) exit 2 ;; esac
cp -a "/work/sources/$project" /tmp/upstream
cd /tmp/upstream
"$@"
if [ "$project" = stdlib ]; then
    mkdir -p /work/sources/stdlib/output
    cp -a output/dfd /work/sources/stdlib/output/
    cp output/home.spm /work/sources/stdlib/output/
else
    mkdir -p /work/sources/plantuml/build/libs
    cp build/libs/*.jar /work/sources/plantuml/build/libs/
fi
