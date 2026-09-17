# rt2 — a clang-cl / lld toolchain for ARM32 Windows (LLVM 23.1.1)

rt2 is a **complete, self-contained toolchain** for compiling C and C++ for **ARM32 Windows**
(`thumbv7`) with `clang-cl` and `lld-link`. It is **LLVM 23.1.1 plus six patches** that upstream
still needs for this target. **If you do not target ARM32 Windows, you do not need it.**

> ### Looking for rt1, rt1.1 or rt1.2 (the LLVM 18.1.8 line)?
> **They live on the [`rt1`](../../tree/rt1) branch.** This repository's `main` always points at the
> newest toolchain; older lines are preserved on their own branches and their releases stay exactly
> as cut. If you are on rt1.x today and it works, **you do not have to move** — read
> *Should you move to rt2?* below before you do.

Base is `llvmorg-23.1.1`. The source tarball's published sha256 was verified before the build:
`ebe9be46fe8756d58c5b198ffad0fa2a766257add81a4dc52179bfacc7888ee6`.

---

## Six patches, not ten — and the four that went away

rt1 needed ten patches to make clang 18 usable on ARM32 Windows. On LLVM 23, **four of them are no
longer necessary**, because upstream fixed them:

| rt1 patch | on LLVM 23 | in rt2 |
|---|---|---|
| **0002** lld writes a local `__imp_` pointer with bit 0 clear | still broken | **carried** |
| **0003** forwarded `musttail` registers not modelled live | still broken | **carried** |
| **0004** CodeView aborts on a tuple-register `DBG_VALUE` | still broken | **carried** |
| **0005** tests for the `this`-adjusting thunk cases in 0003 | — | **carried** |
| **0007** `musttail` vararg forwarder that calls `va_start` aborts | still broken | **carried** |
| **0010** `setjmp` gets the frame pointer, not the entry stack pointer | still broken | **carried** |
| 0001 prologue over-allocates the frame under a split R11/LR push | **fixed upstream** | dropped |
| 0006 `-Wpadded` dead under the MS record layout builder | **fixed upstream** | dropped |
| 0008 crash under `-fdump-record-layouts-complete` | **fixed upstream** | dropped |
| 0009 Windows SEH unsupported on ARM32 | **fixed upstream** | dropped |
| D37 `musttail` to an `sret` function refused | **fixed upstream** | rt1.x never could fix it |

Every "fixed upstream" above was **measured**, not read off a changelog: each row was run against a
compiler known to have the defect and one known not to, and a row where neither arm fired was
recorded as unmeasured rather than as a pass — **11 of 11 rows measured**. The full table lives in
this project's private working repository; it is not in this repository, and `RELEASE-NOTES.md`
carries its published summary.

Two of those are worth naming. **0009 was the largest patch in the rt1 series** at 75,868 bytes, and
it is simply gone. And **D37 is the one defect rt1.x cannot fix at all** — `musttail` to a
struct-returning function is a hard error there and compiles here.

**0002 is carried only because nobody backported it.** The fix is merged on LLVM `main` as
`bfaec6c07`; `release/23.x` branched before it, so it is in no released 23.x. A backport would cut
rt2 to five patches and would help every ARM32 Windows consumer of 23.x, not only this one.

---

## Install

Unpack the release archive and put its `bin/` on your `PATH`, or point your build system at it.
**rt2 overlays nothing and replaces nothing** — that is the difference from rt1.x, which is a
nine-driver overlay onto the official LLVM 18.1.8 package.

> ⚠ **Resource headers are in `lib/clang/23/include`, not `lib/clang/18/include`.** A build system
> carried over from rt1.x that hardcodes `18` will silently find no headers.

### Verifying what you downloaded — read this one carefully

**rt2 and stock upstream LLVM 23.1.1 report the same LLVM version.** The distinguishing string is
the vendor and suffix:

```
findstr /M /C:"23.1.1-rt2" <binary>          (cmd.exe)
grep -ac 23.1.1-rt2 <binary>                 (git-bash/WSL)
```

- the four clang drivers print `Varan clang version 23.1.1-rt2`; stock prints `clang version 23.1.1`
- the five lld drivers print `Varan LLD 23.1.1`; stock prints `LLD 23.1.1`
- the fifteen `llvm-*` tools and `llc` print `LLVM version 23.1.1-rt2`

**And check the other half — no rt1-family commit may be present:**

```
grep -ac 83c117cad0a9dee89e6daf6821c49156a3c562c0 <binary>   -> 0   (rt1.2)
grep -ac 60876c5f8fad221756afd9bbd534377b7ff06571 <binary>   -> 0   (rt1.1)
grep -ac 7653a13d8d28189c7cef1401b934ec30d98ea353 <binary>   -> 0   (rt1 1.0)
```

That second check is not decoration, and neither is the first. An **earlier rt2 build carried no
distinguishing string at all** — it reported `clang version 23.1.1 (llvmorg-23.1.1)`, character for
character what stock upstream reports. A presence-only test against the upstream tag would have
passed on a stock binary. A token the thing you are comparing against also carries cannot tell two
toolchains apart.

`MODIFICATIONS.txt` inside the archive carries the full recipe and the package inventory.

---

## Should you move to rt2?

**Honestly: only if you need something in it.** rt1.2 has more validation behind it; rt2 has a newer
compiler and fewer patches. The real differences:

**Reasons to take rt2**
- Four fewer patches between you and upstream, and one of the four — SEH — was the largest and most
  invasive thing rt1 carried.
- **`musttail` to a struct-returning function works (D37).** rt1.x cannot do this at all — it was a
  reverted candidate there, never one of the shipped ten, so it is a bonus rather than a fifth
  patch removed.
- Five releases of upstream bug fixes, optimisation and diagnostics that have nothing to do with ARM.

**Reasons to stay on rt1.2**
- **rt2's output measured 6.69% larger** than rt1.2's across a 19-binary browser fleet — `xul.dll`
  +6.48%, `mozavcodec.dll` +32.03%. (Stated in the direction it was measured. The reverse figure is
  not the same number: rt1.2 is 6.27% smaller, because percentages are not symmetric.) **No
  investigation into why has been done.**
- rt2 is **stricter**: five releases of newly-promoted errors. A tree that builds clean on rt1.2 may
  need `-Wno-error=...` on rt2. That is modern clang, not an rt2 defect — but it is your afternoon.
- rt1.2 has more miles on it.

---

## What has been measured, and what has not

**rt2 compiles and links a real browser.** The full Varan tree (Pale Moon 34.3.1 / UXP 6.9.0,
ARM32 Windows) was built with rt2 from clean on 2026-09-15:

- **2,537 of 2,537 translation units. 19 of 19 PEs.**
- **Zero ICEs, zero `LLVM ERROR`, zero backend fatals** across the whole tree.
- Every image ARMNT `0x01C4`.
- The `__imp_` gate passed on all 19 **with the post-link fixup scaffold never run** — the
  real-codebase evidence that patch 0002 does what that scaffold used to do by hand.
- The browser launched on a Windows 10 ARM32 device and loaded a page.

**What that does not establish**, stated because it matters more than the headline:

- **One device run, one page.** Not a test suite, not a browsing session. `n=1`.
- **No `longjmp` has been executed on hardware** with an rt2-built binary. Patch 0010 fixes a defect
  that *was* measured on a device; the **fix** has only been measured in the compiler.
- **One open question with a sharp edge.** LLVM 23 tail-calls two call shapes that patch 0007
  deliberately keeps as ordinary calls — including a `byval` argument split between registers and
  the stack. **Stock 23 does this with no rt1 patch applied**, so it is upstream behaviour rt2
  inherits, not something rt2 introduced; upstream grew a mechanism 18.x lacked that presumably
  handles it. **Whether it is actually safe has never been executed.**
- **No Windows RT 8.1 testing**, and no object-by-object corpus comparison.

`RELEASE-NOTES.md` carries the full list. It is long on purpose.

---

## What is here

| | |
|---|---|
| `RELEASE-NOTES.md` | what rt2 fixes, what to expect when moving a tree to it, and — at length — what has **not** been measured |
| `MODIFICATIONS.txt` | the Apache-2.0 §4(b) modification notice and the package inventory |
| `patches/` | **`rt2-vs-23.1.1.patch`** — the complete diff from pristine `llvmorg-23.1.1` to rt2, generated from the two trees and verified by applying it to a fresh 23.1.1 and comparing file for file. `patches/origin/` holds the six original **18.x-targeted** rt1 patches for their defect analysis; they are **not** what rt2 was built from, and `origin/README.txt` says exactly how they differ |
| `runtime/` | the `__aeabi` divmod shim — source plus a prebuilt `.lib`/`.obj` **rebuilt by this compiler**, and a README saying when you need it. It is opt-in, because adding it makes divide-by-zero trap |
| `tools/`, `scratch/` | the instruments and evidence the documents cite |

The `scratch/` paths look internal because they are: they are preserved exactly as the documents
cite them, so every citation resolves to a file you can open. A verdict whose instrument you cannot
inspect is an assertion, not evidence.

`llc` is shipped in `bin/` on purpose, so you can compile the shipped tests yourself rather than
taking our word for anything.

> ⚠ **Do not expect `patches/origin/`'s lit tests to pass against rt2.** They encode LLVM 18.x
> behaviour. 0007's in particular will fail, because LLVM 23 tail-calls two call shapes that 0007
> keeps as ordinary calls — **with no rt1 patch applied at all.** That is upstream behaviour rt2
> inherits, documented under *What has not been measured*, not a defect rt2 introduced.

---

## Maintenance

**rt2 is a one-shot release, like rt1 before it.** No rebases, no version bumps, no maintenance
stream. `main` will move to a newer LLVM if and when one is cut; rt2 will then be preserved on its
own branch exactly as it is now, and its release will not change.


## AI assistance

This toolchain's patches, measurements and documents were produced with substantial AI assistance,
reviewed and directed by a human, who is responsible for what is published here. Every measurement
quoted was executed, not predicted; where something was not measured it is listed as such rather
than omitted.

## Licence, and reporting a problem

Apache License v2.0 with LLVM Exceptions, as LLVM itself — the full text is `LICENSE.TXT` in the
release archive. The eight Microsoft VC runtime DLLs in `bin/` are Microsoft redistributables, are
not modified, and are not covered by that licence — see `MODIFICATIONS.txt`.

**Problems:** open an issue on this repository. This is a one-shot community release with no
maintenance stream, so a fix is not promised — but a reproducer is genuinely useful, and the open
questions in `RELEASE-NOTES.md` are the ones where a real-world report would help most.
