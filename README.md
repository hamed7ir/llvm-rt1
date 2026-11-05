# rt2.2: clang-cl and lld for ARM32 Windows (LLVM 23.1.1)

rt2.2 is LLVM 23.1.1 with 30 patches. I made it because stock LLVM still breaks on ARM32 Windows (`thumbv7`) in a
few places. It's a full toolchain: `clang-cl`, `lld-link`, the LLVM tools, clang's headers and the compiler-rt
libraries, all in one folder. If you don't build for ARM32 Windows, you don't need it.

> **Looking for an older one?** rt2.1 and rt2 are still on their release pages (tags `rt2.1-23.1.1` and
> `rt2-23.1.1`). The LLVM 18.1.8 line (rt1, rt1.1, rt1.2) lives on the [`rt1`](../../tree/rt1) branch. `main` always
> has the newest toolchain, and old releases never change.

## Downloads

Everything is on the release page for tag `rt2.2-23.1.1`. There are three archives. Most people only need the first
one.

| archive | what it is |
|---|---|
| `rt2.2-23.1.1-rt2.2-arm32-win.tar.gz` | **The toolchain.** clang-cl, lld-link, llvm tools, headers, compiler-rt. Start here. |
| `rt2.2-23.1.1-rt2.2-dev-win64.tar.gz` | LLVM's libraries, headers, CMake files and `llvm-config`. Only if you build something against rt2.2's LLVM, like rustc. |
| `rustc-rt2.2-1.100.0-nightly-win64.tar.gz` | rustc built on rt2.2's LLVM, with the standard library for `thumbv7a`, `i686` and `x86_64` Windows. |
| `SHA256SUMS` | sha256 of the three archives. |

All three run on 64-bit x86 Windows. They make programs for ARM32 Windows (and for x86 and x64 too).

## Install

1. Unpack the toolchain archive anywhere.
2. Put its `bin` folder on your `PATH`, or point your build system at it.

It doesn't overlay anything and doesn't need a stock LLVM install. The Microsoft VC runtime DLLs the tools need are
in `bin`. clang's own headers are in `lib/clang/23/include`.

**What you also need.** rt2.2 doesn't include Microsoft's C and C++ headers and libraries or the Windows SDK. For
ARM32 you need Visual Studio 2022 Build Tools with the ARM build tools, and a Windows SDK that still has ARM32
libraries. SDK 10.0.19041 has them. SDK 10.0.26100 doesn't. You can point clang-cl at them like this:

```
clang-cl --target=thumbv7-pc-windows-msvc -fuse-ld=lld -vctoolsdir "<VS>\VC\Tools\MSVC\14.44.35207" -winsdkdir "<Windows Kits>\10" -winsdkversion 10.0.19041.0 hello.c
```

or open a Visual Studio developer prompt, which sets `INCLUDE` and `LIB` for you.

For Chromium (GN), these are the toolchain lines from my args:

```
clang_base_path = "<where you unpacked the toolchain>"
clang_version = "23"
clang_use_chrome_plugins = false    # rt2.2 doesn't have Chromium's clang plugins
```

## Check you got the right build

```
clang-cl --version
```

should print:

```
Varan clang version 23.1.1-rt2.2 (0462bd95317e650684c8dc5ea77dc37eacf59adb)
```

The long number is the first 40 hex digits of the sha256 of `patches/rt22-vs-23.1.1.patch`, the full diff the
toolchain was built from. lld prints only `Varan LLD 23.1.1`, the same as rt2.1's, and most llvm tools print
`LLVM version 23.1.1-rt2.2`.

Don't only trust `--version`. In the `bin` folder, search the file itself. In cmd.exe:

```
findstr /M /C:"0462bd95317e650684c8dc5ea77dc37eacf59adb" clang-cl.exe
```

In git-bash:

```
grep -ac 0462bd95317e650684c8dc5ea77dc37eacf59adb clang-cl.exe
```

If it finds it, it's this build. The sha256 of `clang-cl.exe` is
`4123ae9afbc1913da685f982900a704d0f4ef7a504d62a669fcd76f46e0cbce9` and of `lld-link.exe` is
`b4478942cb384f467af2104f863d397ffea5b731cd8d1d9403552dc59926affa`.

## What's new since rt2.1

rt2.2 keeps rt2.1's 16 patches and adds 14 more. I found the first six while building Venetium, a Chromium-based
browser, for ARM32 Windows with ThinLTO and PGO.

| patch | what was wrong | what you saw |
|---|---|---|
| 0021 | lld's LTO used the PIC model for ARM32 | every `/GS` function failed ThinLTO: "Cannot represent this expression" |
| 0022 | lld's delay-load stubs called the helper with a `bl` (16 MiB reach) | "relocation out of range" linking `chrome.dll` with LTO |
| 0023 | `llvm-lib` didn't know ARM32 bitcode | "unknown arch in target triple" |
| 0024 | the call-graph profile got edges to LLVM intrinsics | `undefined symbol: llvm.exp2.f64` with PGO |
| 0025 | lld's call-graph sort mixed up sections with the same name | the DLL's layout changed between two links of the same files |
| 0026 | Thumb-2 `str` with `pc` assembled with no error | V8's ARM32 port shipped `str.w pc, [sp, #60]`, and Qualcomm devices trap on it |
| B01 to B08 | eight upstream wrong-code fixes that 23.1.1 doesn't have | ARM backend, DAG combiner, InstCombine, GlobalsAA, SimplifyLibCalls |

The toolchain also has `clang_rt.profile-arm.lib` and `clang_rt.profile-i386.lib` now. rt2.1 only had the x86_64
one, and Chromium links these when a build has Rust.

`RELEASE-NOTES.md` has the long version.

**Should you move from rt2.1?** If you use ThinLTO on ARM32, yes: rt2.1's lld can't do those links. Read *Things
that work differently now* first.

## Things that work differently now

- **Thumb-2 `str pc, ...` is an error now**, in inline asm too. It's UNPREDICTABLE on ARM.
- **If you use PGO, gather a new profile with rt2.2.** B06 to B08 change optimizations that run before the profile
  is used.
- **With PGO, a big DLL's layout changes once, then stays the same** on every link.

## How I tested it

Everything ran on my build server:

- 20 new or changed lit tests, on rt2.1 and on rt2.2. The 14 that can fail on rt2.1 fail there because of their bug,
  and pass on rt2.2.
- 17,100 tests in 10 LLVM, clang and lld suites. No test fails on rt2.2 that passes on rt2.1.
- Venetium's real ARM32 ThinLTO and PGO links, `chrome.dll` and V8's `d8.exe`, with rt2.2's lld: no warning. rt2.1's
  lld fails the same `d8.exe` link. Two links of `chrome.dll` came out byte for byte the same.
- compiler-rt: every library is built by rt2.2, with the same code as rt2.1's.
- rustc rebuilt on rt2.2: its standard library has the same code as rt2.1's.

## What I did not test

- Nothing ran on an ARM32 device yet. Venetium is only relinked with rt2.2's lld, not rebuilt with its clang yet.
- B04, B05 and B08 have no test that fails on rt2.1. I kept them anyway.

## rustc

The rustc archive is rustc `1.100.0-nightly (bba531001 2026-09-20)` built on rt2.2's LLVM, with the standard library
for `thumbv7a-pc-windows-msvc`, `i686-pc-windows-msvc` and `x86_64-pc-windows-msvc`. Its own `README.md` says how to
use it. It's a compiler and its standard library only: there is no cargo in it.

## What is in this repository

| | |
|---|---|
| `RELEASE-NOTES.md` | everything that changed, how it was tested, and what was not tested |
| `MODIFICATIONS.txt` | the license notice for changed files, and what is in the toolchain archive |
| `LICENSE.TXT` | LLVM's license, the same file as in the archives |
| `patches/rt22-vs-23.1.1.patch` | the full diff from clean `llvmorg-23.1.1` to rt2.2. This is what the toolchain was built from. |
| `patches/origin/` | every patch on its own. `origin/README.txt` says which ones apply as they are. |
| `runtime/` | the `__aeabi` divide shim: source, and a `.lib`/`.obj` built by this compiler. Opt in only. |
| `tools/`, `scratch/`, `upstream-check/` | tools and evidence from the earlier releases that their documents point to |
| `DISPOSITION-TABLE.md` | the rt1 bug table, kept for history |
| `CURATION-MANIFEST.txt` | the list of files in this repository |

## Maintenance

rt2.2 is a one-shot release, like the ones before it. No rebases and no version bumps. When a newer LLVM line comes,
it takes `main`, and rt2.x moves to its own branch. This release won't change.

## AI assistance

I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the work, and I'm
responsible for what's published here. Every test result above was really run. When something was not tested, I
say so.

## License, and reporting a problem

The toolchain and dev archives, and everything in this repository, are Apache License v2.0 with LLVM Exceptions,
same as LLVM (`LICENSE.TXT`). lld-link and llvm-mt include libxml2, which is MIT (its notice is in `licenses/` in
the archives). The eight Microsoft VC runtime DLLs in `bin` are Microsoft's redistributable files. I didn't change
them and they are not under these licenses (see `MODIFICATIONS.txt`). The rustc archive is Rust's own license (MIT
or Apache-2.0) plus the licenses of the crates inside it, all listed in its `licenses/` folder.

**Problems:** open an issue here. This is a one-shot release, so I can't promise a fix, but a small example that
shows the problem helps a lot.
