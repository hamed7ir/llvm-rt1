# rt2.1: clang-cl and lld for ARM32 Windows (LLVM 23.1.1)

rt2.1 is LLVM 23.1.1 with 16 patches. I made it because stock LLVM still breaks on ARM32 Windows
(`thumbv7`) in a few places. It is a full toolchain: `clang-cl`, `lld-link`, the LLVM tools, clang's
headers and the compiler-rt libraries, all in one folder. If you don't build for ARM32 Windows, you
don't need it.

> **Looking for an older one?** rt2 is still on its release page (tag `rt2-23.1.1`). The LLVM 18.1.8
> line (rt1, rt1.1, rt1.2) lives on the [`rt1`](../../tree/rt1) branch. `main` always has the newest
> toolchain, and old releases never change.

## Downloads

Everything is on the release page for tag `rt2.1-23.1.1`. There are three archives. Most people only
need the first one.

| archive | what it is |
|---|---|
| `rt2.1-23.1.1-rt2.1-arm32-win.tar.gz` | **The toolchain.** clang-cl, lld-link, llvm tools, headers, compiler-rt. Start here. |
| `rt2.1-23.1.1-rt2.1-dev-win64.tar.gz` | LLVM's libraries, headers, CMake files and `llvm-config`. Only if you build something against rt2.1's LLVM, like rustc. |
| `rustc-rt2.1-1.100.0-nightly-win64.tar.gz` | rustc built on rt2.1's LLVM, with the standard library for `thumbv7a`, `i686` and `x86_64` Windows. |
| `SHA256SUMS` | sha256 of the three archives. |

All three run on 64-bit x86 Windows. They make programs for ARM32 Windows (and for x86 and x64 too).

## Install

1. Unpack the toolchain archive anywhere.
2. Put its `bin` folder on your `PATH`, or point your build system at it.

It doesn't overlay anything and doesn't need a stock LLVM install. The Microsoft VC runtime DLLs the
tools need are in `bin`. clang's own headers are in `lib/clang/23/include`. If you came from rt1.x,
watch out: a build file that hardcodes `lib/clang/18` will find no headers here.

**What you also need.** rt2.1 doesn't include Microsoft's C and C++ headers and libraries or the
Windows SDK. Your programs need those to compile and link. For ARM32 you need Visual Studio 2022
Build Tools with the ARM build tools, and a Windows SDK that still has ARM32 libraries. SDK 10.0.19041
has them. SDK 10.0.26100 doesn't. You can point clang-cl at them like this:

```
clang-cl --target=thumbv7-pc-windows-msvc -fuse-ld=lld -vctoolsdir "<VS>\VC\Tools\MSVC\14.44.35207" -winsdkdir "<Windows Kits>\10" -winsdkversion 10.0.19041.0 hello.c
```

or open a Visual Studio developer prompt, which sets `INCLUDE` and `LIB` for you.

For Chromium (GN), these are the toolchain lines from my args:

```
clang_base_path = "<where you unpacked the toolchain>"
clang_version = "23"
clang_use_chrome_plugins = false    # rt2.1 doesn't have Chromium's clang plugins
```

## Check you got the right build

```
clang-cl --version
```

should print:

```
Varan clang version 23.1.1-rt2.1 (e240ad76c3a4429084c026fe0a9b0fce34025032)
```

The long number is the first 40 hex digits of the sha256 of `patches/rt21-vs-23.1.1.patch`, the full
diff the toolchain was built from. So the compiler names the exact source it came from. lld prints
`Varan LLD 23.1.1`, and most llvm tools print `LLVM version 23.1.1-rt2.1`.

Don't only trust `--version`. Open a terminal in the `bin` folder and search the file itself.

In cmd.exe:

```
findstr /M /C:"e240ad76c3a4429084c026fe0a9b0fce34025032" clang-cl.exe
```

In git-bash:

```
grep -ac e240ad76c3a4429084c026fe0a9b0fce34025032 clang-cl.exe
```

If it finds it, it's this build. rt2 doesn't have that string (it prints
`Varan clang version 23.1.1-rt2 (llvmorg-23.1.1)`), so this tells the two apart. The sha256 of
`clang-cl.exe` is `d572c49356dd897ef499131d8914bf6581a8a9a62dcf928220b7db786a1dfed2` and of
`lld-link.exe` is `6e203038eb1b3ac1015f36e3595b456623ca4592c66b998ab0b8ccf0c38afb30`.

## What's new since rt2

rt2 had six patches. rt2.1 keeps all six and adds ten more. I found almost all of these while porting
a Chromium-based browser (Venetium) to ARM32 Windows.

| patch | what was wrong | what you saw |
|---|---|---|
| 0011 | `_ReadWriteBarrier`, `_ReadBarrier` and `_WriteBarrier` were not built in on ARM32 | link error (sqlite hits it) |
| 0012 | 26 MSVC ARM intrinsics were missing, like `_MulHigh`, `_CountLeadingZeros`, `_InterlockedAdd`, `_ReadStatusReg` and `__prefetch`. `_AddressOfReturnAddress` was missing too | compile or link errors |
| 0013 | the `lifetime_capture_by(this)` deprecation warning was on by default | 2,331 `-Werror` errors in Chromium's abseil |
| 0014 | `pcs("aapcs-vfp")` was rejected on Windows on Arm | `-Werror` error in Skia |
| 0015 | lld sent branches that were in range through range thunks that clobber `r12` | **wrong code, no error.** MSVC's `__rt_sdiv` gave wrong remainders and the browser crashed on the device |
| 0016 | ARM objects had no `@feat.00` symbol, so lld ignored their `/guard:cf` tables | under Control Flow Guard the program was killed (`0xC0000409`) on a call through a delay-loaded import |
| 0017 | C++ exceptions were not implemented for ARM32 Windows | the compiler stopped with an error on any `catch` |
| 0018 | lld wrote two bits of the `BRANCH20T` relocation the wrong way round | **wrong code, no error.** Some conditional branches jumped to the wrong place |
| 0019 | a test from rt2 still expected LLVM 18 output | test only, no code change |
| 0020 | finishes `_AddressOfReturnAddress` from 0012: my own first version used the wrong stack slot in some functions | nothing in any release. I found it before anything shipped |

The six from rt2 are still here, because LLVM 23.1.1 still needs them: 0002 (lld lost the Thumb bit
on a local `__imp_` pointer), 0003 and 0005 (registers passed through a `musttail` call), 0004
(CodeView crash on a tuple register), 0007 (`musttail` vararg forwarder with `va_start` crashed) and
0010 (`setjmp` got the frame pointer instead of the stack pointer). 0002 and 0010 are merged in LLVM
main now, but not in any 23.x release. 0003 and 0004 are open pull requests there.

`RELEASE-NOTES.md` has the long version of all of this.

**Should you move from rt2?** Yes, I think so. 0015 and 0018 fix wrong code that lld made with no
warning, and rt2 has both bugs. Read *Things that work differently now* first, though.

## Things that work differently now

- **The new intrinsics are real built-ins now.** If your code defines its own `_CountLeadingZeros`,
  `_ReadWriteBarrier` or similar, you get an error, same as MSVC. Wrap your version in
  `#if !__has_builtin(_CountLeadingZeros)`.
- **C++ exceptions on ARM32 follow MSVC's rules.** A function with `try`/`catch` never gets its
  stack realigned at runtime, like MSVC. Catching by value a type that is aligned to more than 8
  bytes is refused with an error, instead of making code that might be wrong. (MSVC accepts it.)
- **lld-link can embed manifests by itself now**, so you don't need `mt.exe`. `llvm-mt` and
  `llvm-strings` are now in `bin`.
- **libclang.dll is included.** If you load it from another program, give it `-resource-dir`
  pointing at `lib/clang/23`, or it may not find its own headers.

## How I tested it

**On a real ARM32 device:** I built Venetium (a Chromium-based browser) with rt2.1, including its
Rust code with the rustc from this release, and it runs. I also ran three more things on the device,
and all three gave the right result:

- the C++ exception test kit printed the same output as the MSVC build of it,
- with Control Flow Guard enforced, the browser started and worked,
- without the extra `rtdiv` library (patch 0015's case), division gave the right results.

**On my laptop, before that.** Here "the earlier build" means an rt2.1 build I never released: rt2
plus patch 0011, without 0012 to 0020. I kept it only to compare against.

- 197 lit tests. rt2.1 passes all 148 that can run there (the other 49 need targets I didn't build).
  The earlier build fails exactly the 22 tests that are new or changed. So every new test really
  catches its bug.
- 962 source files from two real ARM32 projects (adb and scrcpy, with BoringSSL, protobuf, SDL3 and
  libusb inside): every object came out identical to the earlier build's. I compared code and data,
  not debug info, and ignored the new `@feat.00` symbol. `RELEASE-NOTES.md` says exactly what was
  left out.
- lld: the CFG tables, the `BRANCH20T` encoding (31 cases, checked against MSVC's own `link.exe`)
  and manifest embedding without `mt.exe`. Each check fails on the earlier build.
- LLVM's own libc++ builds with exceptions for ARM32 and links as an ARM32 DLL.
- compiler-rt: all four libraries rebuilt from rt2.1's own source with this compiler.
- libclang: loaded from another program and used to parse a file.
- Intrinsics: MSVC inlines 251 ARM intrinsics. rt2.1 inlines 207 of them now (180 before). Of the
  other 44, 4 are not real gaps and 40 fail loudly with a compile or link error.

Every patch from 0012 on was also reviewed by a separate AI review session that didn't write the
patch and was told to try to break it. I read the reports, and the fixes they asked for were reviewed
again the same way.

## What I did not test

- bindgen. libclang was tested through the same API bindgen uses, but not with bindgen itself.
- Known limits of the C++ exception support, not fixed: an over-aligned local in a function with
  `try`/`catch` loses its debugger location, and each funclet (every `catch` block and every cleanup
  that runs a destructor) reserves its parent's whole stack frame again. So a function with a very
  big frame (around 1/3 MB) can run out of a 1 MB stack while handling an exception. MSVC doesn't do
  that.

## rustc

The rustc archive is rustc `1.100.0-nightly (bba531001 2026-09-20)` built on rt2.1's LLVM. It has the
standard library for `thumbv7a-pc-windows-msvc`, `i686-pc-windows-msvc` and `x86_64-pc-windows-msvc`.
I used it to build Venetium. Its own `README.md` says how to use it. It's a compiler and its standard
library only: there is no cargo in it.

## What is in this repository

| | |
|---|---|
| `RELEASE-NOTES.md` | everything that changed, how it was tested, and what was not tested |
| `MODIFICATIONS.txt` | the license notice for changed files, and what is in the toolchain archive |
| `LICENSE.TXT` | LLVM's license, the same file as in the archives |
| `patches/rt21-vs-23.1.1.patch` | the full diff from clean `llvmorg-23.1.1` to rt2.1. This is what the toolchain was built from. |
| `patches/origin/` | every patch on its own. `origin/README.txt` says which ones apply as they are. |
| `runtime/` | the `__aeabi` divide shim: source, and a `.lib`/`.obj` built by this compiler. Opt in only. |
| `tools/`, `scratch/`, `upstream-check/` | tools and evidence from the earlier releases that their documents point to |
| `DISPOSITION-TABLE.md` | the rt1 bug table, kept for history |
| `CURATION-MANIFEST.txt` | the list of files in this repository |

## Maintenance

rt2.1 is a one-shot release, like rt1 and rt2. No rebases and no version bumps. When a newer LLVM
line comes, it takes `main`, and rt2.x moves to its own branch. This release won't change.

## AI assistance

I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the
work, and I'm responsible for what's published here. Every test result above was really run. When
something was not tested, I say so.

## License, and reporting a problem

The toolchain and dev archives, and everything in this repository, are Apache License v2.0 with LLVM
Exceptions, same as LLVM (`LICENSE.TXT`). lld-link and llvm-mt include libxml2, which is MIT (its
notice is in `licenses/` in the archives). The eight Microsoft VC runtime DLLs in `bin` are
Microsoft's redistributable files. I didn't change them and they are not under these licenses (see
`MODIFICATIONS.txt`). The rustc archive is Rust's own license (MIT or Apache-2.0) plus the licenses
of the crates inside it, all listed in its `licenses/` folder.

**Problems:** open an issue here. This is a one-shot release, so I can't promise a fix, but a small
example that shows the problem helps a lot.
