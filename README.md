# rt2.3: clang-cl and lld for ARM32 Windows (LLVM 23.1.1)

rt2.3 is LLVM 23.1.1 with 32 patches, built with zlib 1.4. I made it because stock LLVM still breaks on ARM32 Windows
(`thumbv7`) in a few places. It's a full toolchain: `clang-cl`, `lld-link`, the LLVM tools, clang's headers and the
compiler-rt libraries, all in one folder. If you don't build for ARM32 Windows, you don't need it.

> **Looking for an older one?** rt2.2, rt2.1 and rt2 are still on their release pages (tags `rt2.2-23.1.1`,
> `rt2.1-23.1.1` and `rt2-23.1.1`). The LLVM 18.1.8 line (rt1, rt1.1, rt1.2) lives on the [`rt1`](../../tree/rt1)
> branch. `main` always has the newest toolchain, and old releases never change.

## Downloads

Everything is on the release page for tag `rt2.3-23.1.1`. There are three archives. Most people only need the first
one.

| archive | what it is |
|---|---|
| `rt2.3-23.1.1-rt2.3-arm32-win.tar.gz` | **The toolchain.** clang-cl, lld-link, llvm tools, headers, compiler-rt. Start here. |
| `rt2.3-23.1.1-rt2.3-dev-win64.tar.gz` | LLVM's libraries, headers, CMake files and `llvm-config`. Only if you build something against rt2.3's LLVM, like rustc. |
| `rustc-rt2.3-1.100.0-nightly-win64.tar.gz` | rustc built on rt2.3's LLVM, with the standard library for `thumbv7a`, `i686` and `x86_64` Windows. |
| `SHA256SUMS` | sha256 of the three archives. |

All three run on 64-bit x86 Windows. They make programs for ARM32 Windows (and for x86 and x64 too).

## Install

1. Unpack the toolchain archive anywhere.
2. Put its `bin` folder on your `PATH`, or point your build system at it.

It doesn't overlay anything and doesn't need a stock LLVM install. The Microsoft VC runtime DLLs the tools need are
in `bin`. clang's own headers are in `lib/clang/23/include`.

**What you also need.** rt2.3 doesn't include Microsoft's C and C++ headers and libraries or the Windows SDK. For
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
clang_use_chrome_plugins = false    # rt2.3 doesn't have Chromium's clang plugins
```

## Check you got the right build

```
clang-cl --version
```

should print:

```
Varan clang version 23.1.1-rt2.3 (ecc7a88742db83ce2316082eb80d23183a8d1e5e)
```

The long number is the first 40 hex digits of the sha256 of `patches/rt23-vs-23.1.1.patch`, the full diff the
toolchain was built from. lld prints only `Varan LLD 23.1.1`, the same as rt2.2's, and most llvm tools print
`LLVM version 23.1.1-rt2.3`.

Don't only trust `--version`. In the `bin` folder, search the file itself. In cmd.exe:

```
findstr /M /C:"ecc7a88742db83ce2316082eb80d23183a8d1e5e" clang-cl.exe
```

In git-bash:

```
grep -ac ecc7a88742db83ce2316082eb80d23183a8d1e5e clang-cl.exe
```

If it finds it, it's this build. The sha256 of `clang-cl.exe` is
`e73fe231cb51c4ab757deda0007afafc8aa64df8fc5c3f587a534c40c888892b` and of `lld-link.exe` is
`d2af70c0aaa4d56bf90ff66a76463e8474ba72b19e0f6e3559a2e4bb4f2b6c9b`.

## What's new since rt2.2

rt2.3 keeps rt2.2's 30 patches and adds 2 more. The work porting Kodi to Windows RT 8.1 ARM32 found both bugs.

| patch | what was wrong | what you saw |
|---|---|---|
| 0027 | on ARM32, clang wrote the C++ throw tables with absolute addresses, and MSVC's runtime reads them as offsets from the image base | every C++ `throw` crashed |
| 0028 | `__ARM_SIZEOF_WCHAR_T` was always 4 | on Windows ARM32 and ARM64, where `wchar_t` is 2 bytes, the macro said 4 |

LLVM is also built with zlib 1.4 now, for Venetium's PGO build. The names in a PGO profile are compressed, so
instrumented objects are smaller, and `llvm-profdata` reads those profiles. `llvm-objcopy` can compress ELF debug
sections.

`RELEASE-NOTES.md` has the long version.

**Should you move from rt2.2?** If you throw C++ exceptions on ARM32, yes. Read *Things that work differently now*
first.

## Things that work differently now

- **Rebuild every ARM32 object that throws a C++ exception, with rt2.3.** Objects from rt2.2 or older still crash
  when they throw.
- **`__ARM_SIZEOF_WCHAR_T` is 2 on Windows ARM32 and ARM64.**
- **Merge PGO profiles from rt2.3's builds with rt2.3's `llvm-profdata`.** rt2.2's can't read them.

## How I tested it

Everything ran on my build server:

- 0027 against MSVC's ARM32 `cl`: rt2.3's throw tables are image-relative where MSVC's are, to the same symbols,
  and the RTTI is absolute like MSVC's.
- 23 lit tests (rt2.2's 20 and rt2.3's 3) on rt2.2 and on rt2.3. rt2.3's 3 fail on rt2.2 because of their bug and
  pass on rt2.3. rt2.2's 20 give the same results on both.
- 19,256 tests in 14 LLVM, clang and lld suites: rt2.2's 10 and four more for 0027, 0028 and zlib. No test fails on
  rt2.3 that passes on rt2.2, and the 15 zlib tests rt2.2 skipped pass now.
- zlib: a PGO round trip on i686 works with the rt2.3 tools, and rt2.2's `llvm-profdata` can't read its profile.
- compiler-rt: every library is built by rt2.3, with the same code as rt2.2's.
- rustc rebuilt on rt2.3: its standard library has the same code as rt2.2's.

## What I did not test

- Nothing ran on an ARM32 device yet. 0027 is checked against MSVC's objects, not by throwing on a device.
- Venetium isn't rebuilt with rt2.3 yet.

## rustc

The rustc archive is rustc `1.100.0-nightly (bba531001 2026-09-20)` built on rt2.3's LLVM, with the standard library
for `thumbv7a-pc-windows-msvc`, `i686-pc-windows-msvc` and `x86_64-pc-windows-msvc`. Its own `README.md` says how to
use it. It's a compiler and its standard library only: there is no cargo in it.

## What is in this repository

| | |
|---|---|
| `RELEASE-NOTES.md` | everything that changed, how it was tested, and what was not tested |
| `MODIFICATIONS.txt` | the license notice for changed files, and what is in the toolchain archive |
| `LICENSE.TXT` | LLVM's license, the same file as in the archives |
| `patches/rt23-vs-23.1.1.patch` | the full diff from clean `llvmorg-23.1.1` to rt2.3. This is what the toolchain was built from. |
| `patches/origin/` | every patch on its own. `origin/README.txt` says which ones apply as they are. |
| `runtime/` | the `__aeabi` divide shim: source, and a `.lib`/`.obj` built by this compiler. Opt in only. |
| `tools/`, `scratch/`, `upstream-check/` | tools and evidence from the earlier releases that their documents point to |
| `DISPOSITION-TABLE.md` | the rt1 bug table, kept for history |
| `CURATION-MANIFEST.txt` | the list of files in this repository |

## Maintenance

rt2.3 is a one-shot release, like the ones before it. No rebases and no version bumps. When a newer LLVM line comes,
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
