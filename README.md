# rt2.4: clang-cl and lld for ARM32 Windows (LLVM 23.1.1)

rt2.4 is LLVM 23.1.1 with 38 patches, built with zlib 1.4. I made it because stock LLVM still breaks on ARM32 Windows
(`thumbv7`) in a few places. It's a full toolchain: `clang-cl`, `lld-link`, the LLVM tools, clang's headers and the
compiler-rt libraries, all in one folder. If you don't build for ARM32 Windows, you don't need it.

> **Looking for an older one?** rt2.3, rt2.2, rt2.1 and rt2 are still on their release pages (tags `rt2.3-23.1.1`,
> `rt2.2-23.1.1`, `rt2.1-23.1.1` and `rt2-23.1.1`). The LLVM 18.1.8 line (rt1, rt1.1, rt1.2) lives on the
> [`rt1`](../../tree/rt1) branch. `main` always has the newest toolchain, and old releases never change.

## Downloads

Everything is on the release page for tag `rt2.4-23.1.1`. There are three archives. Most people only need the first
one.

| archive | what it is |
|---|---|
| `rt2.4-23.1.1-rt2.4-arm32-win.tar.gz` | **The toolchain.** clang-cl, lld-link, llvm tools, headers, compiler-rt. Start here. |
| `rt2.4-23.1.1-rt2.4-dev-win64.tar.gz` | LLVM's libraries, headers, CMake files and `llvm-config`. Only if you build something against rt2.4's LLVM, like rustc. |
| `rustc-rt2.4-1.100.0-nightly-win64.tar.gz` | rustc built on rt2.4's LLVM, with the standard library for `thumbv7a`, `i686` and `x86_64` Windows. |
| `SHA256SUMS` | sha256 of the three archives. |

All three run on 64-bit x86 Windows. They make programs for ARM32 Windows (and for x86 and x64 too).

## Install

1. Unpack the toolchain archive anywhere.
2. Put its `bin` folder on your `PATH`, or point your build system at it.

It doesn't overlay anything and doesn't need a stock LLVM install. The Microsoft VC runtime DLLs the tools need are
in `bin`. clang's own headers are in `lib/clang/23/include`.

**What you also need.** rt2.4 doesn't include Microsoft's C and C++ headers and libraries or the Windows SDK. For
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
clang_use_chrome_plugins = false    # rt2.4 doesn't have Chromium's clang plugins
```

## Check you got the right build

```
clang-cl --version
```

should print:

```
Varan clang version 23.1.1-rt2.4 (f6e5f8e02a8c69d0479b5623215b8a8b8fcd2e01)
```

The long number is the first 40 hex digits of the sha256 of `patches/rt24-vs-23.1.1.patch`, the full diff the
toolchain was built from. lld prints only `Varan LLD 23.1.1`, the same as rt2.3's, and most llvm tools print
`LLVM version 23.1.1-rt2.4`.

Don't only trust `--version`. In the `bin` folder, search the file itself. In cmd.exe:

```
findstr /M /C:"f6e5f8e02a8c69d0479b5623215b8a8b8fcd2e01" clang-cl.exe
```

In git-bash:

```
grep -ac f6e5f8e02a8c69d0479b5623215b8a8b8fcd2e01 clang-cl.exe
```

If it finds it, it's this build. The sha256 of `clang-cl.exe` is
`f24b35ac6539a117afca2cf67a87e7d80b0e3c9d5ed981dbe7884664040f1d27` and of `lld-link.exe` is
`2f4ab430a7a680b90d12d1e947654646457f20cbae65442fd9c156c9239c0070`.

## What's new since rt2.3

rt2.4 keeps rt2.3's 32 patches and adds 6 more. The work porting Kodi to Windows RT 8.1 ARM32 found five of them. I
found 0030 while sending the C++ exception work upstream.

| patch | what was wrong | what you saw |
|---|---|---|
| 0029 | on ARM32, clang wrote 20-byte catch handler entries, and MSVC's runtime reads 16 | the second or a later `catch` of a `try` jumped to garbage |
| 0030 | the code after a `catch` was placed inside the catch funclet | an exception thrown there was handled as if it came from inside the catch |
| 0031 | a call that doesn't return could be the last instruction of a function or funclet, so its return address was in the next one | MSVC's runtime unwound through the wrong function: a rethrow was caught again and again until the stack overflowed |
| 0032 | the constant pools didn't count the padding before each funclet | some functions with `try`/`catch` didn't compile: "out of range pc-relative fixup value" |
| 0033 | `llvm-objdump` kept the Thumb bit in an ARM32 DLL's export addresses | `llvm-objdump -d` decoded every export one byte off |
| 0034 | my own 0030 got one case wrong: a catch block with debug info | with `/Zi`, some catch blocks didn't compile: "Incorrect size for ... epilogue" |

`RELEASE-NOTES.md` has the long version.

**Should you move from rt2.3?** If you use C++ exceptions on ARM32, yes. Read *Things that work differently now*
first.

## Things that work differently now

- **Rebuild every ARM32 object that throws or catches a C++ exception, with rt2.4.** Objects from rt2.3 or older keep
  the old catch tables and code layout.
- **A 2-byte trap follows every call that doesn't return** on ARM32 Windows, like MSVC does. Code gets a little
  bigger.

## How I tested it

On my Surface RT, by the Kodi port: its C++ exception test passes all 56 cases in Release and debug builds, Kodi
built with rt2.4 runs and plays video with sound, and FFmpeg's and dav1d's assembly tests pass. Kodi RT 1.1's
kodi.exe and its FFmpeg are built with this final rt2.4.

On my build server:

- Against MSVC's ARM32 `cl`: rt2.4's catch handler entries are 16 bytes like MSVC's, the code after a catch is in the
  parent function like MSVC's, and the Kodi port's exception test program has no call that ends a function, like
  MSVC's build.
- 29 lit tests (rt2.2's 20, rt2.3's 3 and rt2.4's 6) on rt2.3 and on rt2.4. rt2.4's 6 fail on rt2.3 because of their
  bug and pass on rt2.4. The other 23 give the same results on both.
- 19,260 tests in 14 LLVM, clang and lld suites. No test fails on rt2.4 that passes on rt2.3.
- compiler-rt: every library is built by rt2.4. The x86 and x64 ones have the same code as rt2.3's, and the ARM ones
  differ only by 0031's traps.
- rustc rebuilt on rt2.4: its standard library has the same code as rt2.3's, except 0031's traps in the C profiler
  runtime it bundles.

## What I did not test

- The exception test didn't run on the device with this exact build. It gives the same code as the build that ran,
  except the version string.
- Venetium isn't rebuilt with rt2.4 yet.

## rustc

The rustc archive is rustc `1.100.0-nightly (bba531001 2026-09-20)` built on rt2.4's LLVM, with the standard library
for `thumbv7a-pc-windows-msvc`, `i686-pc-windows-msvc` and `x86_64-pc-windows-msvc`. Its own `README.md` says how to
use it. It's a compiler and its standard library only: there is no cargo in it.

## What is in this repository

| | |
|---|---|
| `RELEASE-NOTES.md` | everything that changed, how it was tested, and what was not tested |
| `MODIFICATIONS.txt` | the license notice for changed files, and what is in the toolchain archive |
| `LICENSE.TXT` | LLVM's license, the same file as in the archives |
| `patches/rt24-vs-23.1.1.patch` | the full diff from clean `llvmorg-23.1.1` to rt2.4. This is what the toolchain was built from. |
| `patches/origin/` | every patch on its own. `origin/README.txt` says which ones apply as they are. |
| `runtime/` | the `__aeabi` divide shim: source, and a `.lib`/`.obj` built by this compiler. Opt in only. |
| `tools/`, `scratch/`, `upstream-check/` | tools and evidence from the earlier releases that their documents point to |
| `DISPOSITION-TABLE.md` | the rt1 bug table, kept for history |
| `CURATION-MANIFEST.txt` | the list of files in this repository |

## Maintenance

rt2.4 is a one-shot release, like the ones before it. No rebases and no version bumps. When a newer LLVM line comes,
it takes `main`, and rt2.x moves to its own branch. This release won't change.

## AI assistance

I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the work, and I'm
responsible for what's published here. Every test result above was really run. When something was not tested, I
say so.

## License, and reporting a problem

The toolchain and dev archives, and everything in this repository, are Apache License v2.0 with LLVM Exceptions,
same as LLVM (`LICENSE.TXT`). lld-link and llvm-mt include libxml2, which is MIT, and the tools include zlib, under
the zlib license (their notices are in `licenses/` in the archives). The eight Microsoft VC runtime DLLs in `bin` are
Microsoft's redistributable files. I didn't change them and they are not under these licenses (see
`MODIFICATIONS.txt`). The rustc archive is Rust's own license (MIT or Apache-2.0) plus the licenses of the crates
inside it, all listed in its `licenses/` folder.

**Problems:** open an issue here. This is a one-shot release, so I can't promise a fix, but a small example that
shows the problem helps a lot.
