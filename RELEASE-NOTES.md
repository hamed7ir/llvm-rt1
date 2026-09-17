# rt2 — release notes

rt2 is a **complete toolchain** for compiling C and C++ for **ARM32 Windows** (`thumbv7`) with
`clang-cl` and `lld-link`. It is **LLVM 23.1.1 plus six patches**. If you do not target ARM32
Windows, you do not need it.

**To install:** unpack it and put `bin/` on your PATH, or point your build system at it directly.
Unlike rt1, rt1.1 and rt1.2 — which are overlays onto the official LLVM 18.1.8 package — **rt2
replaces nothing and overlays nothing.** It is self-contained.

> ⚠ **Its resource headers live in `lib/clang/23/include`, not `lib/clang/18/include`.** A build
> system carried over from rt1.x that hardcodes `18` will silently find no headers.

---

## Why rt2 exists, and what it is not

rt1 was built because clang 18 miscompiled ARM32 Windows in ways that produced **silently wrong
binaries**. Ten patches later, rt1.2 is a toolchain that works — and it is frozen on an old base.

rt2 answers a different question: **how much of that is still necessary on a modern LLVM?** The
answer, measured row by row: **four of the ten are fixed upstream and dropped**, leaving six.

| rt1 patch | on LLVM 23.x | in rt2 |
|---|---|---|
| **0002** lld local `__imp_` Thumb bit | still broken | **carried** |
| **0003** forwarded `musttail` registers | still broken | **carried** |
| **0004** CodeView tuple-register abort | still broken | **carried** |
| **0005** this-adjust thunk tests | rides with 0003 | **carried** |
| **0007** `musttail` vararg + `va_start` | still broken | **carried** |
| **0010** `setjmp` entry stack pointer (D42) | still broken | **carried** |
| 0001 ARM frame split-push | **fixed upstream** | dropped |
| 0006 MS-layout padding diagnostics | **fixed upstream** | dropped |
| 0008 `-fdump-record-layouts-complete` crash | **fixed upstream** | dropped |
| 0009 ARM32 Windows SEH | **fixed upstream** | dropped |
| D37 `musttail` to an `sret` function | **fixed upstream** | n/a — rt1.2 never could |

Every "fixed upstream" above was measured with an instrument that was shown to be capable of
reporting the opposite — a defective arm and a fixed arm both present in the same run — not assumed
from a changelog: **11 of 11 rows measured, none left unmeasured.** The full table lives in this
project's private working repository as `RT2-3-RESULTS.md` and is **not part of this package or the
public repository** — the summary above is the published form of it.

**Two of those deserve naming.** 0009 (SEH) was the largest patch in the rt1 series at 75,868 bytes,
and it is simply gone — upstream implemented ARM32 Windows SEH. And **D37 is the one defect rt1.2
cannot fix**: `musttail` to a struct-returning function is a hard error on rt1.2 and compiles on
rt2. That is the one comparison that does not favour the older release, and it is stated here
because a reader choosing between them deserves it.

**0002 is carried only because nobody backported it.** The fix is merged on LLVM `main` as
`bfaec6c07`; `release/23.x` branched before it, so it is in no released 23.x. A backport would cut
rt2 to five patches and would help every ARM32 Windows consumer of 23.x, not just this one.

---

## What has actually been measured

**rt2 compiles and links a real browser.** On 2026-09-15 the full Varan tree — Pale Moon 34.3.1 on
UXP/Goanna 6.9.0, targeting ARM32 Windows — was built with rt2 from clean:

- **2,537 of 2,537 translation units compiled. 19 of 19 PEs linked.**
- **Zero ICEs, zero `LLVM ERROR`, zero backend fatal errors** across the whole tree.
- Every produced image and every sampled object carries the ARMNT machine word `0x01C4`.
- The `__imp_` gate passed on all 19 PEs **with the post-link fixup scaffold never run** — which is
  the evidence that patch 0002 does on a real codebase what that scaffold used to do by hand.
- The resulting browser launched on a Windows 10 ARM32 device and loaded a page without crashing.

That is rt2's first real consumer, and before it rt2 had nothing but its own lit tests.

### One build difference you should expect

rt2's first pass over that tree produced **11 errors**, all one root cause:
`-Wincompatible-pointer-types`, where 32-bit `int*` is passed to a Win32 API declaring
`unsigned long*`. **This is not an rt2 defect** — clang 16 promoted that class from warning to
error, and the identical diagnostic appears at the identical file and column as a *warning* under
rt1.2. All the sites were in vendored third-party code (NSPR, ffvpx) and are benign on 32-bit
Windows, where `int`, `unsigned int` and `unsigned long` are all 32 bits.

Expect this generally: **rt2 is five LLVM releases newer than rt1.2, and it is stricter.** New
warnings and newly-promoted errors in your tree are modern clang doing its job, not rt2 misbehaving.
`-Wno-error=incompatible-pointer-types` is the usual first reach.

### Size

Across those 19 PEs, rt2's output totalled **6.69% larger** than rt1.2's — `xul.dll` +6.48%,
`mozavcodec.dll` +32%, one PE slightly smaller. **No investigation into why has been done.** It is
reported because it is a real difference a consumer will see, not because it is understood.

---

## What has NOT been measured

This section is long deliberately. rt2 is young, and the honest summary is **"it builds a browser,
and that is all it has earned."**

- **No `longjmp` has been executed on ARM32 hardware with an rt2-built binary.** Patch 0010 fixes a
  defect that was *measured on a device* (`STATUS_BAD_STACK` on a `longjmp`), but the **fix** has
  never been run there. The evidence for 0010 is compiler-side only.
- **The tail-call scope question is open, and it is rt2's sharpest edge.** LLVM 23 tail-calls two
  call shapes that rt1's patch 0007 deliberately keeps as ordinary calls — including a `byval`
  argument split between registers and the stack, which 0007's own test calls "the hazard being
  preserved". **Stock 23 does this with no rt1 patch applied**, so it is upstream behaviour that rt2
  inherits rather than anything rt2 introduced; upstream grew a `ByValNeedsCopyForTailCall`
  mechanism that 18.x lacked and presumably handles it. **Whether it is actually safe has never
  been executed.** Whether the shape even occurs in the Varan tree is also unanswered: the obvious
  source search is invalid by construction, because clang marks an ARM argument `byval` only above
  64 bytes.
- **One device run, one page.** Not a test suite, not a browsing session, no wasm, no GC pressure,
  no long run. `n=1`.
- **No Windows RT 8.1 testing.** The single device observation is Windows 10 ARM32 only.
- **No object-by-object corpus comparison.** rt1.1 earned its claim that way (2,582 TUs compiled
  twice, 2,581 byte-identical); nothing equivalent was run for rt2, and across a five-release gap
  byte-identity would not have been the right bar anyway.
- **One gate unmeasured.** The thunk-class gate needs a map-retaining relink that was not performed,
  on either toolchain. Its floors are also calibrated against 18.1.8 and may not transfer.
- **The SEH and D37 paths are unexercised by that corpus**, not validated by it.
- **`llvm-lib` archive interchangeability with 18.1.8's was not checked.**

**Would we ship a product built with rt2 today?** Not without more than this. rt2 has earned "it
builds a large real C++ codebase without crashing the compiler", which is a genuine result and more
than most one-shot toolchains can say. It has not earned "this is known-good for production ARM32".

---

## Provenance and honesty

The six changes are ours. What ships in `patches/` is **`rt2-vs-23.1.1.patch`** — the complete diff
from pristine `llvmorg-23.1.1` to rt2, generated from the two source trees and verified by applying
it to a fresh 23.1.1 and comparing the result file for file. `llc` is included in `bin/` so you can
compile the shipped tests yourself.

⚠ **`patches/origin/` holds the original 18.x-targeted rt1 patches, and they are NOT what rt2 was
built from.** Two differ materially: 0004 was re-anchored for a 23.x API rename, and **three of
0007's four hunks are deliberately absent** because 23.1.1 passes `CallLoweringInfo` into the
function those hunks thread a parameter through. Their lit tests will **not** pass on rt2 — 0007's
especially, for the upstream tail-call reason described above. They are kept for their defect
analysis, which is worth reading and does not change.

Upstream drafts exist for several of these defects and filing them is an ongoing, separate effort;
one earlier fix from this project (the lld Thumb-bit patch, `bfaec6c07`) is already merged upstream.

**AI assistance:** this toolchain's patches, measurements and documents were produced with
substantial AI assistance, reviewed and directed by a human. Every measurement quoted here was
executed, not predicted; where something was not measured it is listed above rather than omitted.

Apache License v2.0 with LLVM Exceptions, as LLVM itself — the full text is `LICENSE.TXT` beside
this file. The eight Microsoft VC runtime DLLs in `bin/` are Microsoft's redistributables and are
not covered by that licence — see `MODIFICATIONS.txt`.

**Reporting a problem:** open an issue on the repository. This is a one-shot release with no
maintenance stream, so a fix is not promised — but a reproducer is genuinely useful, especially for
the byval tail-call question above, which is the one open item nobody has executed.
