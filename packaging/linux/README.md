# Native Linux / PikaOS build

This fork enables and validates the existing Linux runtime for PikaOS 4 x86-64.
It runs the original x86-64 game code with the port's system-library runtime and
Vulkan renderer. Supply your own plaintext game dump (`eboot.bin`, `sce_module`,
`sce_sys`, and game assets). No game assets are shipped in the build archive.

## Build from source

Use GCC with C++23 support (GCC 14 or later recommended), CMake >=3.24 and Python 3.
On PikaOS 4 / recent Debian:

```bash
sudo apt install build-essential cmake ninja-build pkgconf git python3 python3-pil python3-tk \
  libsdl3-dev libvulkan-dev libx11-dev glslang-tools libfmt-dev libboost-dev \
  robin-map-dev libvulkan-memory-allocator-dev libxxhash-dev libzydis-dev \
  libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libswresample-dev
git submodule update --init --recursive
bash build.sh
```

If base tools, SDL3/Vulkan/X11 headers and FFmpeg runtime libraries are already
installed, the remaining development packages can instead be extracted privately:

```bash
bash packaging/linux/pikaos-deps.sh
bash build.sh
```

This downloads packages from your configured APT repositories to `out/deps` and
does not use sudo or change installed packages. Headers must match installed
FFmpeg runtime versions. The script targets the package names in PikaOS 4; use
system packages on distributions with other ABI versions. `build.sh` and
`play-linux.sh` automatically load this private dependency prefix. Set
`CMAKE_BUILD_PARALLEL_LEVEL=4` to control compiler jobs (default 4), and
`THEORDER_LTO=OFF` for a faster, less memory-intensive development build.

The executable is `out/theorder-probe`, with `out/gpu/libtheordergpu.so`. Keep the
non-PIE executable and GS-based guest TLS settings: the guest uses 40-bit tagged
pointers and glibc must retain its own FS-based TLS.

## Run

Open the graphical launcher to select your game folder and adjust resolution,
display mode, frame rate and upscaling:

```bash
bash launcher-linux.sh
```

The same window is available through `bash play-linux.sh --settings`. While the
game runs, **Insert** (or **R3 + L2** on a controller) opens its settings overlay.
Temporal upscaling is experimental for this game and requires the launcher's
experimental-upscaler switch. Availability of FSR/DLSS variants depends on their
assets, optional bridges and GPU support; the Linux package does not include the
Windows DLSS bridge or optional FSR 4 model downloads.

From the checkout or the extracted native archive:

```bash
bash play-linux.sh --game-dir '/path/to/game'
```

Set `THEORDER_GAME_DIR` to remember the game location in your shell. Writable
settings, generated images, saves and shader caches default to
`${XDG_DATA_HOME:-$HOME/.local/share}/theorder1886`; `THEORDER_DATA_DIR` overrides
this. The source game files are read without modification. Use `--perf` for the
upstream lighter engine options. `--clean-vulkan` disables implicit Vulkan layers
for this launch, useful when an installed overlay or frame-generation layer fails.

Pipeline binary caching is off by default on Linux: NVIDIA 595.104.02 on the
validation machine corrupts a preserved register in `vkGetPipelineKeyKHR`.
Ordinary shader/pipeline compilation remains enabled. `THEORDER_PIPELINE_BINARIES=1`
opts in for testing other drivers. Fixed-offset startup tracing is also opt-in
(`THEORDER_STARTUP_TRACE=1`), and unrelated small images are rejected before patching.
Linux game mounts tolerate unique case differences in asset names; writable saves
retain the host filesystem's case behavior.

The native archive uses your system's Python, Pillow, Tk (for the launcher), SDL3,
X11 and Vulkan driver.
When built with the local bootstrap, it also ships the private FFmpeg, fmt and
Zydis shared libraries; their remaining dependencies come from PikaOS. It targets
PikaOS 4, not older distributions with older glibc/library ABIs.
Build it with `bash packaging/linux/package-native.sh`. The archive and SHA256
checksum are written to `dist/`. The optional existing AppImage build requires
PyInstaller and additional packaging tools; the native archive avoids those.

## Verify

```bash
bash play-linux.sh --cpu-features
bash play-linux.sh --clean-vulkan --vulkan-only
python3 -m unittest discover -s tests
bash build.sh --test
```

The Vulkan smoke test checks command submission and a 4096-byte readback. Actual
game graphics additionally require Vulkan 1.3 and the renderer's device features.
Keyboard/controller mappings and diagnostics are described in the root README.
For a bounded game smoke test, use `--timeout 30`; watchdog termination at that
limit is expected and does not mean a clean gameplay exit.

## Validation status

See `docs/linux-port-research.md` in the source checkout for source analysis and
`docs/linux-validation.md` for the measured build/runtime results. Successful
compilation and Vulkan checks alone do not establish complete gameplay, sound,
save/load, or support for every game region and graphics driver.
