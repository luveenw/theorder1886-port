#!/usr/bin/env bash
# Source from build/run scripts. Local packages are optional; system installs also work.
theorder_deps_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)/out/deps/root/usr
if [[ -d $theorder_deps_root ]]; then
    export CMAKE_PREFIX_PATH="$theorder_deps_root${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
    export PKG_CONFIG_PATH="$theorder_deps_root/lib/x86_64-linux-gnu/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
    export LD_LIBRARY_PATH="$theorder_deps_root/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
unset theorder_deps_root
