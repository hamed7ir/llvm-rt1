# rt2.1 release notes

**Build:** 2026-10-05, clang `e240ad76c3a4429084c026fe0a9b0fce34025032`.
`clang-cl --version` prints `Varan clang version 23.1.1-rt2.1 (e240ad76c3a4429084c026fe0a9b0fce34025032)`.

rt2.1 is a full toolchain for C and C++ on ARM32 Windows (`thumbv7`) with `clang-cl` and `lld-link`.
It is LLVM 23.1.1 with 16 patches. It doesn't overlay anything: unpack it and use it. clang's own
headers are in `lib/clang/23/include`.

It does **not** include Microsoft's C and C++ headers and libraries or the Windows SDK. You need
those to build programs. For ARM32 that means Visual Studio 2022 Build Tools with the ARM build tools,
and a Windows SDK that still has ARM32 libraries (10.0.19041 has them, 10.0.26100 doesn't). Point
clang-cl at them with `-vctoolsdir` and `-winsdkdir`, or use a Visual Studio developer prompt.

The revision in the version string is the first 40 hex digits of the sha256 of
`patches/rt21-vs-23.1.1.patch`, the full diff from clean `llvmorg-23.1.1`. So you can check which
source a binary came from.

## The 16 patches

Six come from rt2, which got them from rt1. LLVM 23.1.1 still needs them:

| patch | what it fixes | upstream |
|---|---|---|
| 0002 | lld: a locally defined dllimport function's `__imp_` pointer lost the Thumb bit | merged in LLVM main (PR 215919), not in 23.x |
| 0003 | ARM: registers forwarded through a `musttail` call were not treated as live | open pull request (PR 222468) |
| 0004 | CodeView: a tuple register in a `DBG_VALUE` crashed the backend | open pull request (PR 222347) |
| 0005 | tests for the `this`-adjusting thunk cases of 0003 | |
| 0007 | ARM: a `musttail` vararg forwarder that also calls `va_start` crashed the backend | |
| 0010 | clang: `_setjmp` on Windows ARM32 got the frame pointer instead of the entry stack pointer | merged in LLVM main (PR 222366), not in 23.x |

Ten are new in rt2.1. I found almost all of them while porting a Chromium-based browser (Venetium)
to ARM32 Windows:

| patch | what was wrong | what you saw without it | tests |
|---|---|---|---|
| 0011 | `_ReadWriteBarrier`, `_ReadBarrier`, `_WriteBarrier` were not built in on 32-bit Arm | an external call that fails to link (sqlite hits it), and a `-Wignored-pragma-intrinsic` warning | 3 test files |
| 0012 | 26 MSVC ARM intrinsics were missing: `_MulHigh`, `_MulUnsignedHigh`, the `_Count*`, `_InterlockedAdd*` and `_Copy*` families, `_ReadStatusReg`, `__prefetch`. `_AddressOfReturnAddress` was missing too | compile error, or a call to a function that doesn't exist | 8 clang tests |
| 0013 | the `lifetime_capture_by(this)` deprecation warning was on by default | 2,331 `-Werror` errors in Chromium 150's abseil | 1 new, 1 changed |
| 0014 | `pcs("aapcs-vfp")` was rejected on Windows on Arm, where it is already the default | `-Werror` error in Skia | 2 |
| 0015 | lld sent branches that were in range through range-extension thunks once its safety margin grew. Those thunks clobber `r12` | **wrong code, no error.** MSVC's `__rt_sdiv` keeps a value in `r12`, so remainders came back negated and the browser crashed on the device | 4 (one is ARM64) |
| 0016 | ARM COFF objects had no `@feat.00` symbol, so lld ignored their `/guard:cf` tables | under Control Flow Guard, a fast-fail (`0xC0000409`) on the first call through an address-taken delay-loaded import | 1 |
| 0017 | C++ exception handling (WinEH, `__CxxFrameHandler3`) was not implemented for Windows ARM32 | the backend stopped with an error on any `catch`. A function that only had cleanups compiled with no error but got a broken exception table (from reading the CRT source, I expect that to end in `terminate()`; I didn't run it) | 3 new, 2 changed |
| 0018 | lld wrote the J1 and J2 bits of `IMAGE_REL_ARM_BRANCH20T` the wrong way round | **wrong code, no error.** Some conditional branches landed 256 KB away from their target | 1 |
| 0019 | rt2's copy of 0007's test still had LLVM 18 expectations | the test failed on rt2 itself. Test only, no code change | (test only) |
| 0020 | finishes `_AddressOfReturnAddress` from 0012. A leaf function now saves LR so there is a slot to point at, and on ELF Thumb2 the push is split at r7 | nothing in any release: my own first version of 0012 had the wrong slot, and I fixed it before anything shipped | 1 |

Every new test fails on the earlier build (see *How it was tested*) and passes on rt2.1. Every patch
from 0012 on was reviewed by a separate AI review session that didn't write it and was told to try to
break it. I read the reports, and the changes they asked for were reviewed again.

## Things that work differently now

Read this before you rebuild a big tree with rt2.1.

- **Defining one of the new built-ins is now an error.** You'll see
  `definition of builtin function '_CountLeadingZeros'` or `conflicting types`. MSVC rejects the same
  code (C2169), so this matches MSVC. But code that brought its own `_CountLeadingZeros` and friends
  for an older clang will break. Wrap it in `#if !__has_builtin(_CountLeadingZeros)`. On one project
  I measured, 714 of its 727 source files (all of its C++ files) hit this, all through one
  force-included header.
- **The three barriers (0011) are built in now, too.** Defining `_ReadWriteBarrier`, `_ReadBarrier`
  or `_WriteBarrier` yourself, declaring one with another type, or taking its address is now an
  error, same as on x86. They are compiler barriers only and emit no instruction, like MSVC on ARM.
- **C++ exceptions on ARM32 follow MSVC's rules, limits too.** A function with C++ exception
  funclets never gets its stack realigned at runtime. That's MSVC's contract. Compiler temporaries
  stay 8-byte aligned, and an `alignas` local above 8 bytes is placed at an aligned address inside a
  bigger block. One case can't work this way, and rt2.1 **refuses it with an error** instead of
  making code that may be wrong: catching **by value** a type that is aligned above 8 bytes. MSVC
  19.44 accepts that code and puts the catch object at a fixed offset that is not guaranteed to be
  aligned.
- **Each funclet reserves its parent's whole frame again.** That's every `catch` block and every
  cleanup that runs a destructor. A function with a frame bigger than about 1/3 MB can run out of a
  1 MB stack while it handles an exception. MSVC's funclets don't do that. Not changed.
- **No `/GS` cookie in functions with exception funclets.** That's general LLVM behaviour, x64 does
  the same. It's not special to ARM.
- **`@feat.00` also carries the `-guard:ehcont` bit** now, the same bit MSVC's ARM compiler sets, so
  lld should read ARM `.gehcont$y` tables too. I did not run `-guard:ehcont` on a device.
- **0013 is different from upstream's default** for that one warning. `-Wdeprecated-attributes`
  turns it back on.
- **`llvm-mt.exe` and `llvm-strings.exe` are included now**, and `lld-link` embeds and merges
  manifests by itself (it has libxml2 built in). You don't need `mt.exe` on `PATH`.
- **libclang.dll is included.** If another program loads it, it may not find its own
  `lib/clang/23` headers unless you pass `-resource-dir`. With that, it behaves exactly like `clang`.
- **compiler-rt:** `lib/clang/23/lib/windows/` has all four libraries (`clang_rt.builtins-arm.lib`,
  `-i386.lib`, `-x86_64.lib`, `clang_rt.profile-x86_64.lib`), all built by this compiler from rt2.1's
  own source.

## How it was tested

**On a real ARM32 device.** I built Venetium with rt2.1, including its Rust code with the rustc from
this release, and it runs on an ARM32 Windows device. I also ran three more things there, and all
three gave the right result:

- the C++ exception test kit printed the same output as the MSVC build of it,
- with Control Flow Guard enforced, the browser started and worked,
- without the staged `rtdiv` library (the case patch 0015 fixes), division gave the right results.

**On the build laptop (2026-10-05).** "The earlier build" below is an rt2.1 build I never released:
rt2 plus patch 0011, without 0012 to 0020. I kept it only to compare against. (Compared with rt2
itself, the 0011 tests would differ too.)

- **lit:** 197 tests, run on rt2.1 and on the earlier build. rt2.1 passes all 148 that can run there.
  The other 49 need LLVM targets that weren't built. The earlier build fails exactly the 22 tests
  that are new or changed.
- **Regression check:** 962 source files from two real ARM32 projects, adb and scrcpy (with
  BoringSSL, protobuf, SDL3 and libusb inside), all built for `thumbv7`. Every object is identical to
  the earlier build's, after I removed from both sides the debug-info section (`.debug$S`, which
  holds the version string) and the address-significance table (that table was compared separately
  by symbol name), zeroed the timestamps, and ignored the new `@feat.00` symbol. So this checks code
  and data, not debug info. One thing had to change for this check: the 727 adb files force-include
  a header that defines `_CountLeadingZeros`, which now fails (see above). I wrapped those
  definitions in `#if !__has_builtin(...)` for both compilers. Planted test cases were all sorted the
  way they should be.
- **Linker:** the CFG tables (0016), the `BRANCH20T` encoding for 31 branch distances checked
  against MSVC's own `link.exe` (0018), and manifest embedding without `mt.exe`. Each check also
  fails on the earlier build, so it really can fail.
- **C++ exceptions:** LLVM's own libc++ builds with exceptions for ARM32 and links as an ARM32 DLL.
  The exception test kit gives identical output with MSVC and with rt2.1 on x86, and on the device
  as said above.
- **compiler-rt:** all four libraries, plus the staged `rtdiv` one, rebuilt from rt2.1's own source
  with this compiler. They match the earlier build's libraries member for member, apart from the
  expected `@feat.00`. The i386 and x86_64 libraries ran a test program.
- **libclang:** loaded from another program and used to parse a file through the same API that
  bindgen uses.
- **Intrinsics:** MSVC inlines 251 ARM intrinsics. rt2.1 inlines 207 of them (180 on the earlier
  build). Of the other 44, 4 are not real gaps and 40 fail loudly with a compile or link error.

## What was not tested

- bindgen itself. libclang was tested through the API bindgen uses.
- 0020's bad slot on the earlier code. No build without 0020 but with 0012 exists, so I never ran it.
- An over-aligned local in a function with C++ exception funclets loses its debugger location. Not
  fixed.
- Two rarely used SelectionDAG paths still assume a temporary's preferred alignment. A sweep of
  4,271 functions built to find them never reached either one. Not fixed.

## Where it came from

The toolchain was built from `patches/rt21-vs-23.1.1.patch`. I checked it two ways: applied as one
diff to a clean `llvmorg-23.1.1`, and as rt2's diff plus patches 0011 to 0020 in order. Both give the
same tree, file for file. `patches/origin/` has every patch on its own. See its `README.txt`.

I have upstream drafts written for most of the new fixes. Sending them upstream is separate work.

**AI assistance:** I made the patches, tests and documents with a lot of help from AI. I directed
and reviewed the work. Every test result here was really run. What was not tested is listed above.

**License:** Apache License v2.0 with LLVM Exceptions, same as LLVM. See `LICENSE.TXT`. lld-link and
llvm-mt include libxml2, which is MIT (its notice is in `licenses/`). The Microsoft VC runtime DLLs in
`bin/` are Microsoft's redistributable files and are not under either license. See
`MODIFICATIONS.txt`.
