# Linux and PikaOS port research

Research date: 2026-10-16. Baseline inspected: upstream commit
`3cbef75de0f33e431e19a0dfe391e530057f739e`. This records source analysis and host
observations; successful compilation and gameplay are separate validation steps.

## Scope and existing Linux support

Upstream describes a native x86-64 CPU runtime plus the shadPS4 Vulkan graphics core.
Its published validation covers Windows/NVIDIA and the CUSA00035 01.02 dump. It
explicitly lists Linux, other regions, AMD/Intel graphics, sound, saving/loading,
and gameplay beyond the prologue as unverified. The game data must be supplied
separately; the repository does not include it. A Linux executable cannot establish
that all of those gameplay features work. Source: [upstream README](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/README.md).

The existing `build.sh` already has a Linux path: a shared `libtheordergpu.so`, a
non-PIE `theorder-probe`, and a Vulkan capability tool. `gpu/CMakeLists.txt` needs
CMake >=3.24 and C++23. Most dependencies use system CMake/pkg-config packages;
magic_enum and miniz have vendored fallbacks. LibAtrac9, ImGui, sirit/SPIR-V headers,
Xbyak, and FSR-Vulkan are available in the source/submodules. Source:
[build.sh](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/build.sh),
[GPU CMake configuration](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/gpu/CMakeLists.txt).

`run.py` already branches for Windows/Linux, locates game data with
`THEORDER_GAME_DIR`, and supports a separate writable `THEORDER_DATA_DIR`.
`run.sh` builds before starting unless `THEORDER_PREBUILT` is set. Existing Linux
AppImage packaging freezes a Tk launcher and intentionally excludes host graphics
drivers and glibc from bundling. Its suitability must be checked against the final
Linux build. Source: [run.py](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/run.py),
[run.sh](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/run.sh),
[Linux packaging](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/packaging/linux/build.sh).

## PikaOS dependency mapping

The target's `/etc/os-release` identifies PikaOS 4, codename `nest`,
`ID_LIKE=debian`, `DEBIAN_CODENAME=sid`. This matches the
[official PikaOS wiki](https://wiki.pika-os.com/en/home). Use the target's Pika
repositories; adding Debian repositories is unnecessary.

The following package names are present in this target's APT metadata, checked
with `apt-cache policy` on the research date. They map directly to requirements in
the [GPU CMake configuration](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/gpu/CMakeLists.txt)
and [build script](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/build.sh):

```sh
sudo apt-get install \
  build-essential git cmake ninja-build pkgconf \
  libsdl3-dev libvulkan-dev libfmt-dev libboost-dev \
  robin-map-dev libvulkan-memory-allocator-dev libxxhash-dev libzydis-dev \
  glslang-tools libavcodec-dev libavformat-dev libavutil-dev \
  libswscale-dev libswresample-dev libx11-dev \
  python3 python3-pil
```

Debian's primary package indexes independently confirm
[libsdl3-dev](https://packages.debian.org/sid/libsdl3-dev),
[robin-map-dev](https://packages.debian.org/sid/robin-map-dev), and
[libzydis-dev](https://packages.debian.org/sid/libzydis-dev). Debian's
[VMA install manifest](https://sources.debian.org/src/vulkan-memory-allocator/3.4.0%2Bdfsg-1/debian/libvulkan-memory-allocator-dev.install)
confirms `libvulkan-memory-allocator-dev` provides both its header and CMake config.

Host observations before dependency installation: CMake 4.3.4, SDL3 3.4.16,
Vulkan headers/loader 1.4.357, glslang 16.2, and Mesa 26.2.5 are already installed.
APT candidates include fmt 10.1, Boost 1.90, Zydis 4.1.1, VMA 3.4, and FFmpeg
9.0.1. Several development packages above are absent. These versions are host
observations, not a proposed minimum-version contract; compiling against this
FFmpeg generation is an important compatibility check.

Optional additions:

- `vulkan-tools` and `vulkan-validationlayers`: diagnostics; already installed here.
- `python3-venv` plus the `iced-x86==1.21.0` wheel: ISA preparation on older CPUs.
  No `python3-iced-x86` candidate appears in this host's APT metadata. The Python
  scanner imports it conditionally. Source: [ISA scanner](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/scripts/isa_rewrite.py).
- `spirv-cross`: optional FSR4 post-pass optimization in `run.sh`, not required by
  the main GPU CMake dependency list. PyInstaller/Tk/AppImage tooling is needed
  only for the existing frozen GUI/AppImage packaging route.

## Runtime constraints to preserve

The guest executes x86-64 code directly. Linux guest TLS is deliberately placed
behind GS using `arch_prctl(ARCH_SET_GS)`; image preparation rewrites guest FS
loads to GS so glibc retains FS. Preserve this division. Linux documents that FS
belongs to runtime TLS and GS can be application-owned, while `ARCH_SET_GS` can be
restricted by kernel/security configuration. Sources:
[runtime_thread.c](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/src/runtime_thread.c),
[Linux kernel FS/GS documentation](https://docs.kernel.org/arch/x86/x86_64/fsgs.html).

The loader uses a non-PIE executable and glibc allocation tuning to keep guest
visible host pointers below 1 TiB because the guest packs pointers into 40 bits.
Its POSIX fault path installs SIGSEGV/SIGBUS/SIGILL/SIGTRAP handlers and forwards
eligible faults to GPU tracking/ISA handling. Preserve `-no-pie`, exported runtime
symbols, fixed guest address mappings, and the signal-context ABI when changing
the build. Sources: [probe.c](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/src/probe.c),
[build.sh](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/build.sh).

The CPU check requires SSE4.2, POPCNT, and AVX; missing MOVBE, BMI1, LZCNT, and
F16C are classified separately for rewriting. The scanner currently marks F16C
sites unsupported, so do not promise complete support for every AVX-era CPU.
Sources: [cpu_check.c](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/src/cpu_check.c),
[ISA scanner](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/scripts/isa_rewrite.py).

## Vulkan and display validation

The renderer requests Vulkan 1.3 and asserts support for `VK_KHR_swapchain`,
`VK_KHR_push_descriptor`, `VK_EXT_vertex_attribute_divisor`, and
`VK_EXT_robustness2`, followed by required robustness feature bits. A loader/API
version check alone is insufficient. Sources: [vk_platform.h](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/gpu/shadps4/video_core/renderer_vulkan/vk_platform.h),
[vk_instance.cpp](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/gpu/shadps4/video_core/renderer_vulkan/vk_instance.cpp).
Khronos explains that extension enumeration and feature-bit queries are separate
checks: [enabling Vulkan extensions](https://docs.vulkan.org/guide/latest/enabling_extensions.html).

SDL window integration already obtains native handles for both X11 and Wayland.
The build still explicitly links X11. Validate the user's actual desktop session;
`SDL_VIDEODRIVER=x11` is a useful fallback diagnostic on a Wayland desktop with
XWayland. Source: [window.cpp](https://github.com/mateussmeneses/theorder1886-port/blob/3cbef75de0f33e431e19a0dfe391e530057f739e/gpu/shim/window.cpp).
SDL's Linux documentation describes runtime-loaded display/audio features and
controller/udev troubleshooting: [SDL3 Linux notes](https://wiki.libsdl.org/SDL3/README-linux).

Recommended acceptance sequence: dependency/configuration checks; Python tests;
Linux runtime tests; CPU and Vulkan probes; loader startup with the user's dump;
then visible title/prologue rendering and input/audio/save checks. Keep compile,
driver initialization, and verified gameplay results distinct in the release
notes. This sequence is an engineering recommendation inferred from the source's
separate build/runtime paths and upstream's stated validation limits.
