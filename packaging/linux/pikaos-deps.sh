#!/usr/bin/env bash
# Extract development packages from the configured PikaOS/Debian APT repository locally.
# Does not run maintainer scripts, install packages globally, or require sudo.
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
for tool in apt-get dpkg-deb python3; do
    command -v "$tool" >/dev/null || { echo "Need $tool (PikaOS/Debian)." >&2; exit 1; }
done
packages=(libavcodec-dev libavutil-dev libavformat-dev libswscale-dev libswresample-dev
          libfmt-dev libfmt10 libboost-dev robin-map-dev libvulkan-memory-allocator-dev
          libzydis-dev libzydis4.1 libzycore-dev libzycore1.5)
# The default Boost development package depends on a versioned header package.
boost=$(apt-cache depends libboost-dev | sed -n 's/.*Depends: \(libboost[0-9.]*-dev\).*/\1/p' | head -1)
[[ -n $boost ]] || { echo 'Cannot resolve Boost headers from APT.' >&2; exit 1; }
packages+=("$boost")
# Development .so links name the matching runtime file; keep both in the prefix.
for dev in libavcodec-dev libavutil-dev libavformat-dev libswscale-dev libswresample-dev; do
    while read -r runtime; do packages+=("$runtime"); done < <(
        apt-cache depends "$dev" | sed -n 's/.*Depends: \(lib\(avcodec\|avutil\|avformat\|swscale\|swresample\)[0-9][0-9]*\).*/\1/p')
done
mkdir -p out/deps/packages out/deps/root
(cd out/deps/packages && apt-get download "${packages[@]}")
for package in out/deps/packages/*.deb; do dpkg-deb -x "$package" out/deps/root; done
python3 - <<'PY'
from pathlib import Path
root = Path('out/deps/root/usr').resolve()
for path in root.rglob('*.pc'):
    text = path.read_text()
    # Derive prefix from each file's location so checkouts can be moved.
    relative = Path(__import__('os').path.relpath(root, path.parent)).as_posix()
    lines = text.splitlines()
    lines = [f'prefix=${{pcfiledir}}/{relative}' if s.startswith('prefix=') else s for s in lines]
    lines = [s.replace('=/usr/', '=${prefix}/') for s in lines]
    path.write_text('\n'.join(lines) + '\n')
PY
echo 'Local headers/libraries ready. Build with: bash build.sh'
echo 'Base tools, SDL3, Vulkan, X11 and matching FFmpeg runtime libraries must be installed (see README.md).'
