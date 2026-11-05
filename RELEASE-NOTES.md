# rt2.2 release notes

**Build:** 2026-11-04, clang `0462bd95317e650684c8dc5ea77dc37eacf59adb`.
`clang-cl --version` prints `Varan clang version 23.1.1-rt2.2 (0462bd95317e650684c8dc5ea77dc37eacf59adb)`.

rt2.2 is rt2.1 with 14 more patches, so 30 in all. The base is still LLVM 23.1.1. It's a full toolchain for C
and C++ on ARM32 Windows (`thumbv7`) with `clang-cl` and `lld-link`. It doesn't overlay anything: unpack it and
use it. clang's own headers are in `lib/clang/23/include`.

It does **not** include Microsoft's C and C++ headers and libraries or the Windows SDK. For ARM32 you need Visual
Studio 2022 Build Tools with the ARM build tools, and a Windows SDK that still has ARM32 libraries (10.0.19041 has
them, 10.0.26100 doesn't).

The revision in the version string is the first 40 hex digits of the sha256 of `patches/rt22-vs-23.1.1.patch`,
the full diff from clean `llvmorg-23.1.1`. So you can check which source a binary came from.

## What's new since rt2.1

Six patches are mine. I found these bugs while building Venetium, a Chromium-based browser, for ARM32 Windows with
ThinLTO and PGO:

| patch | what was wrong | what you saw without it | tests |
|---|---|---|---|
| 0021 | lld's LTO used the PIC model for ARM32 | every function with `/GS` failed ThinLTO code generation: "Cannot represent this expression" | 1 new |
| 0022 | lld's delay-load stubs called the helper with a `bl`, which reaches only 16 MiB | with LTO the helper lands far away: "relocation out of range" linking `chrome.dll` | 1 new, 1 changed |
| 0023 | `llvm-lib` didn't know ARM32 bitcode | "unknown arch in target triple: thumbv7-pc-windows-msvc" | 1 new |
| 0024 | the call-graph profile got edges to LLVM intrinsics | with PGO: `undefined symbol: llvm.exp2.f64` linking V8's `d8.exe` | 1 new |
| 0025 | lld's call-graph sort gave all sections with the same leader name one priority, picked by heap order | `chrome.dll`'s layout changed between two links of the same files | 2 new |
| 0026 | Thumb-2 `str` with `pc` as the register to store assembled with no error and decoded with no warning | V8's ARM32 port shipped `str.w pc, [sp, #60]`. It's UNPREDICTABLE, and Qualcomm devices trap on it at startup (`c000001d`) | 2 new, 1 changed |

Eight are fixes from upstream LLVM for wrong code or crashes. They are not in 23.1.1, and I took all of them:

| patch | upstream | what it fixes |
|---|---|---|
| B01 | #231702 | ARM: wrong code in multiply-accumulate on 64-bit values |
| B02 | #226937 | ARM: the load/store optimizer kept stale register liveness after it erased an instruction |
| B03 | #223396 | DAGCombiner: a borrow chain rebuilt without a 0/1 carry-in |
| B04 | #224759 | DAGCombiner: `combineOrOfSetCCToUSUBOCarry` only for 0/1 booleans |
| B05 | #229620 | SelectionDAG: undef lanes of a bitcast were taken as known zero |
| B06 | #226783 | InstCombine: wrong code in `sinkNotIntoOtherHandOfLogicalOp` |
| B07 | #213631 | GlobalsAA: a store of a global's address into itself |
| B08 | #231159 | SimplifyLibCalls: a constant built from a signed `char` |

They keep their upstream authors and messages. B02 needed its context changed to apply, because 23.1.1's code next
to it is older. Its own lines are upstream's.

**Two compiler-rt libraries rt2.1 was missing** are in `lib/clang/23/lib/windows/` now: `clang_rt.profile-arm.lib`
and `clang_rt.profile-i386.lib`. rt2.1 only had the x86_64 one. Chromium links these when a build has Rust, so I
had to add them by hand for Venetium. They are built the same way as the x86_64 one. On ARM32, clang-cl finds
`clang_rt.profile-arm.lib` by itself only when the target is spelled `arm`, like Chromium's `--target=arm-windows`.
With `thumbv7` it asks for a `clang_rt.profile.lib` that isn't in the package. The toolchain's `README.md` says what
to do then.

Every new patch from 0021 to 0026 was reviewed by a separate AI session that didn't write it and was told to break
it. I read the reports, and the fixes they asked for were reviewed again.

## Things that work differently now

- **`str pc, ...` in Thumb-2 is an error now** (0026), in `.s` files and in inline asm too. `str.w pc, [sp, #60]`
  gives "operand must be a register in range [r0, r14]". One line of LLVM's own `basic-thumb2-instructions.s` test
  had to go for this. The disassembler warns "potentially undefined instruction encoding" on those encodings now.
- **With PGO, the layout of a big DLL changes once, then stays.** Sections that share a name now each keep their own
  place in the call-graph sort (0025). In Venetium's `chrome.dll` that moves 61 sections under 4 names. Two links of
  the same files now give the same bytes.
- **If you use PGO, gather a new profile with rt2.2.** B06 to B08 change optimizations that run before the profile
  is used, so a profile from rt2.1 may not match everywhere. I'm gathering a new one for Venetium.
- `lld-link --version` still prints `Varan LLD 23.1.1`, with no rt2.2 in it. Check lld by its sha256.

## How it was tested

Everything here ran on my build server, not on an ARM32 device.

- **lit:** all 20 new or changed tests ran on the published rt2.1, on rt2.1's source rebuilt here, on an rt2.2 test
  build and on the rt2.2 binaries in this archive. 14 fail on rt2.1 because of their bug and pass on rt2.2. Of the
  other six: two need targets I didn't build (AArch64 and PowerPC), two only show their bug with assertions on
  (B08), one checks what 0025 must not change, and one is the changed `basic-thumb2-instructions.s`.
- **Suites:** 17,100 tests in 10 suites: ARM and X86 CodeGen, ARM MC and its disassembler, lld COFF, clang
  CodeGen, InstCombine, Instrumentation, GlobalsModRef and llvm-lib. No test fails on rt2.2 that passes on a test
  build of rt2.1's source. The only failure on both is rt2.1's own `arm-thumb-thunks-no-converge.s`, which loses
  lld's message inside the real llvm-lit. By hand lld prints the right error.
- **0026:** the instruction list from my bug report. Exactly the three accepted forms now error and their three
  encodings now warn. The other eight lines come out the same as rt2.1's.
- **Venetium's real links:** I relinked Venetium's ARM32 ThinLTO and PGO build with rt2.2's lld, from the same
  objects (they were compiled by rt2.1's clang).
  - `chrome.dll` and V8's `d8.exe` link with no warning (`/WX`). On the same `d8.exe` link, the published rt2.1 lld
    fails with "Cannot represent this expression", and my earlier lld without 0024 fails with
    `undefined symbol: llvm.exp2.f64`.
  - In `chrome.dll`, all 612,690 `/GS` cookie loads in the LTO code are absolute, with their relocations. All 59
    delay-load stubs call the helper through an absolute address, and the helper is 119 MiB away from them.
  - Two links of `chrome.dll` gave the same DLL, PDB and map, byte for byte. Against rt2.2 without 0025, only
    sections with a shared name moved, under 4 names: `ReadHuffmanCode` (libwebp's and brotli's, the pair I first
    saw), two libc++ initializers, ICU's `compareUnicodeString`, and 58 copies of one logging constructor.
- **compiler-rt:** all six libraries and the staged `rtdiv` one are built by rt2.2. They have the same code and data
  as the same libraries built by rt2.1, member for member. With rt2.1's compiler, the same recipe gives the same
  members as the libraries rt2.1 shipped.
- **Headers:** all 303 files in `lib/clang/23/include` are rt2.1's, byte for byte.

## What was not tested

- Nothing ran on an ARM32 device yet: not the relinked `chrome.dll`, not the new profile libraries, and not the
  Rust standard library for `thumbv7a`.
- Venetium isn't rebuilt with rt2.2's clang yet, only relinked with its lld. That full build, with a new PGO
  profile, comes next.
- B04, B05 and B08 have no test that fails on rt2.1. B08's tests only fail with assertions on. B05's only test is
  for PowerPC. B04 has no upstream test, and its own commit message says no in-tree target can reach that code yet.
  I kept all three.
- In my two test links with the old sort, the 0025 bug didn't flip. The lit test shows what the old sort gets wrong.
- 0022's failure wasn't seen in the real link, because I have no lld with 0021 but not 0022. The lit test shows it.

## Where it came from

The toolchain was built from `patches/rt22-vs-23.1.1.patch`: rt2.1's tree plus the 14 new patches in order (0021 to
0026, then B01 to B08), as one `git diff --binary` from clean `llvmorg-23.1.1`. I checked it by applying it to a
clean tree: it gives the same tree as the commits it was made from. `patches/origin/` has every patch on its own. See
its `README.txt`.

rt2.1's diff had a header of its own. rt2.2's is a plain git diff. Both apply with `git apply`.

I'll send the six new fixes upstream. That's separate work.

**AI assistance:** I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the
work. Every test result here was really run. What was not tested is listed above.

**License:** Apache License v2.0 with LLVM Exceptions, same as LLVM. See `LICENSE.TXT`. lld-link and llvm-mt include
libxml2, which is MIT (its notice is in `licenses/`). The Microsoft VC runtime DLLs in `bin/` are Microsoft's
redistributable files and are not under either license. See `MODIFICATIONS.txt`.
