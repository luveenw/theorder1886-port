#!/usr/bin/env bash
# Graphical settings and Play button, using the same runtime environment as direct play.
set -euo pipefail
exec bash "$(dirname -- "$0")/play-linux.sh" --settings "$@"
