# PikaOS Linux validation

Validated on 2026-10-16, starting from upstream commit
`3cbef75de0f33e431e19a0dfe391e530057f739e`. The fork's implementation lives on
`codex/pikaos-linux` at https://github.com/luveenw/theorder1886-port.

## Machine and build

- PikaOS 4 (`nest`, Debian-based), x86-64, kernel `7.2.6-pikaos`.
- AMD Ryzen 7 5800XT, 32 GiB RAM; required CPU instructions reported complete.
- NVIDIA GeForce RTX 5070 Ti, proprietary driver `595.104.02`, Vulkan 1.4.
- GCC 16.2.0, CMake 4.3.4, SDL3 3.4.16 and FFmpeg 9 development/runtime packages.
- `THEORDER_LTO=OFF bash build.sh --test` produces the native ELF executable
  `out/theorder-probe`, `out/gpu/libtheordergpu.so`, and the GPU capability tool.
  The no-root bootstrap supplies missing libraries under `out/deps`.

## Changes needed

1. Correct quoting of pkg-config flags for paths containing spaces, complete
   dependency/submodule checks, bounded compiler concurrency, and local APT
   dependency extraction with relocatable pkg-config metadata.
2. Resolve the Debian Zydis package's unqualified `Zycore` dependency to the
   exported `Zycore::Zycore` CMake target.
3. Keep physical allocations inside their caller's exclusive upper bound;
   never round that bound upward. Boundary regression tests pass.
4. Resolve unique case differences in read-only game asset paths on Linux.
   The tested dump contains `ps4/GPU` while its game code requests `ps4/gpu`.
   Exact names take priority and writable save paths retain their usual behavior.
5. Return an empty add-on list for nonzero service labels when no add-ons are
   mounted. CUSA00785 calls this API with service label 1 during startup.
6. Make fixed-offset diagnostic patching opt-in and reject incompatible small
   images. Remove the invented main initializer at offset `0x20` for images
   without initializer metadata; the game's entry already invokes its initializer.
7. Default pipeline binary caching off on Linux, including the GUI launcher.
   A focused real-device test reproducibly crashes when it is enabled on this
   NVIDIA driver. GDB confirmed the dispatch pointer equals the driver's own
   `vkGetDeviceProcAddr` result and that the call corrupts the preserved RBX
   register. Normal compilation and shader caching remain available.
8. Add direct and graphical Linux entry points, restore the launcher's visible
   experimental FSR 3.1/TAA/output-resolution controls, and package a native archive.
9. Replace the shader compiler's fixed 32 MiB executable SRT-walker arena with
   additional nonmoving chunks. Cache warm-up and new shader compilation share
   this storage; cached helper code could fill it before the opening scene.
   Generate each new walker privately before publishing it, and recognize all
   chunks in the fault handler, including helpers loaded only from cache.
10. Add Reset to Default beside Save on every launcher page. Reset is staged
    until Save/Play, removes obsolete runtime overrides, restores controls and
    retains game/save/content locations and selections. Saves/caches are untouched.

## Checks

- `python3 -m unittest discover -s tests`: 247 tests, pass; 42 skips in the
  sandbox (Windows-only, optional iced-x86 and display-dependent tests).
- With desktop display access, 81 launcher/control/entry-point tests run with
  16 Windows-only skips. The passing tests include the real Tk resolution and
  upscaling controls, reset/save/reopen, failed-save retry and save/cache retention.
- The native runtime suite passes: pad input, threads/TLS/synchronization,
  direct memory, files, content services, MP3/H.264 decoding, services and ISA stubs.
- Renderer checks pass: pipeline binary serialization, initialization/fallbacks,
  motion history and PNG decoding. The initialization test uses the real GPU
  with binary caching disabled, then exercises mocked failure/success cases.
- Vulkan command submission and a 4096-byte GPU readback pass on the RTX 5070 Ti.
- The Tk launcher opens all five pages and its Graphics page successfully.
- The SRT regression registers 105 MiB through the real cached-walker API,
  including concurrent registration and a single 33 MiB blob, and executes every
  retained function pointer after growth. The initial 40 MiB reproduction failed
  before the fix with the exact `code is too big` exception.

## Game validation and limits

The supplied CUSA00785 version 01.02 dump prepares and links successfully
(`eboot.bin` SHA256
`0e22cc57718c4e02fc5c2bb5e059905828c277f02206a783d16fe0a45aab81e1`).
A 60-second run rendered opening logos, animated backgrounds and the save notice,
with 10,020 submitted flips and 11 five-second statistics windows. No host/guest
fault occurred. It ended with the requested watchdog, status 142, rather than a
normal user exit. Intro presentation was uncapped, so that flip count is not a
claim about gameplay FPS.

A separate 120-second run with `THEORDER_FPS_LIMIT=30` progressed into the
prologue cutscene (a character close-up was checked in a frame capture),
submitted 3,540 flips, and produced 23 five-second statistics windows averaging
28.4–30.0 FPS. Stable warmed windows had a 33.33 ms median frame time. It also
created a 102,400-byte `SYSTEM.DAT` in the isolated save folder. No host/guest
fault occurred; the requested watchdog again ended the run with status 142.
This verifies startup and initial scene rendering, not the full campaign or a
save/load round trip.

### Warm-cache startup crash

The reported exit 23 after the SCE/SMS logos was reproduced using copies of the
user's settings and populated shader cache (about 488 MB), without clearing it.
GDB caught Xbyak's exception during a new SRT walker emission and showed
`g_srt_codegen.size_ == maxSize_ == 33554432`. The disk shader cache itself has
no 32 MiB limit; this was executable CPU helper storage shared by cached and new
shaders. Local history already contains the allocation in its imported baseline
and does not document why that size was chosen. Missing `.meta` messages preceded
the failure but were cache misses, not the fatal assertion.

With expandable storage, the same settings and cache ran for 90 seconds, reaching
flip 5,160 instead of failing at flip 480. The requested watchdog ended the run
with status 142; no `code is too big` or GPU assertion occurred. No cache purge or
user preference changes were needed. This is a startup regression check, not
full-game validation.

Run logs and decoded frame captures are under `out/` and are intentionally not
committed. Test saves/settings are isolated in `out/linux-smoke`; the source game
dump was not modified. Full gameplay, audio listening, save/load round trips,
other GPU drivers and temporal-upscaler image quality remain unverified. Optional
DLSS bridges and FSR 4 model assets are not included in the native archive.

## Use

`bash launcher-linux.sh` opens settings and the Play button. Graphics contains
the experimental upscaler, quality preset and output resolution. `Insert` or
controller `R3 + L2` opens the in-game display/performance overlay.
See [the Linux instructions](../packaging/linux/README.md) for dependencies,
direct launch, diagnostic switches and archive creation.
