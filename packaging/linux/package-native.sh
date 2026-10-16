#!/usr/bin/env bash
# A native archive for the current PikaOS host; graphics drivers remain host-provided.
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
[[ -x out/theorder-probe && -f out/gpu/libtheordergpu.so ]] || { echo 'Build first: bash build.sh' >&2; exit 1; }
target=out/theorder1886-linux-x86_64
rm -rf -- "$target"
mkdir -p "$target/bin/gpu" "$target/lib" "$target/launcher" dist
install -m755 out/theorder-probe out/theorder-gpu-capabilities "$target/bin/"
install -m755 out/gpu/libtheordergpu.so "$target/bin/gpu/"
install -m755 play-linux.sh launcher-linux.sh "$target/"
cp run.py LICENSE "$target/"
cp README.md "$target/SOURCE-README.md"
cp -r scripts patches "$target/"
install -m644 launcher/theorder.png "$target/launcher/"
cp launcher/*.py "$target/launcher/"
cp packaging/linux/README.md "$target/README.md"
mkdir -p "$target/docs" "$target/licenses"
for note in docs/linux-*.md; do cp "$note" "$target/docs/"; done
# These are the private runtime packages used by the no-root bootstrap, when present.
shopt -s nullglob
for lib in out/deps/root/usr/lib/x86_64-linux-gnu/*.so.*; do
    cp -L "$lib" "$target/lib/"
done
for copyright in out/deps/root/usr/share/doc/*/copyright; do
    package=$(basename -- "$(dirname -- "$copyright")")
    cp "$copyright" "$target/licenses/$package.txt"
done
strip --strip-unneeded "$target/bin/theorder-probe" "$target/bin/theorder-gpu-capabilities" \
    "$target/bin/gpu/libtheordergpu.so"
for elf in "$target/bin/theorder-probe" "$target/bin/gpu/libtheordergpu.so"; do
    missing=$(LD_LIBRARY_PATH="$PWD/$target/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd "$elf" | grep 'not found' || true)
    [[ -z $missing ]] || { echo "$missing" >&2; exit 1; }
done
find "$target" -type d -name __pycache__ -prune -exec rm -rf {} +
tar -C out -czf dist/theorder1886-linux-x86_64.tar.gz theorder1886-linux-x86_64
(cd dist && sha256sum theorder1886-linux-x86_64.tar.gz > theorder1886-linux-x86_64.tar.gz.sha256)
echo "Created $PWD/dist/theorder1886-linux-x86_64.tar.gz"
