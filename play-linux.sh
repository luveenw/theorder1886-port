#!/usr/bin/env bash
# Run a built Linux checkout or extracted native Linux package.
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -f packaging/linux/deps-env.sh ]]; then source packaging/linux/deps-env.sh; fi
export LD_LIBRARY_PATH="$PWD/lib:$PWD/bin/gpu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export THEORDER_DATA_DIR=${THEORDER_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/theorder1886}
settings=0
while (( $# )); do
    case $1 in
        --game-dir)
            [[ $# -ge 2 ]] || { echo '--game-dir needs a folder' >&2; exit 2; }
            export THEORDER_GAME_DIR=$2; shift 2 ;;
        --clean-vulkan)
            export VK_LOADER_LAYERS_DISABLE='~implicit~'; shift ;;
        --settings) settings=1; shift ;;
        --help)
            echo 'Usage: ./play-linux.sh [--game-dir /path/to/game] [--clean-vulkan] [game options]'
            echo 'Diagnostics: --cpu-features, --vulkan-only. Game options: --perf, --level NAME, --timeout SECONDS.'
            echo 'Settings window: --settings (or run launcher-linux.sh).'
            echo 'THEORDER_GAME_DIR and THEORDER_DATA_DIR override game and writable data locations.'
            exit 0 ;;
        *) break ;;
    esac
done
if (( settings )); then
    exec "${PYTHON:-python3}" launcher/port_launcher_win.py "$@"
fi
probe=out/theorder-probe
[[ -x bin/theorder-probe ]] && probe=bin/theorder-probe
[[ -x $probe ]] || { echo 'Build first: bash build.sh' >&2; exit 1; }
case ${1:-} in
    --cpu-features|--vulkan-only|--gamepad) exec "$probe" "$@" ;;
esac
exec "${PYTHON:-python3}" run.py "$@"
