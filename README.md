# rt1.2 — a one-shot clang-cl / lld overlay for ARM32 Windows (LLVM 18.1.8)

rt1.2 is a small **binary overlay** onto the official LLVM 18.1.8 win64 package, for people
compiling C and C++ for **ARM32 Windows** (`thumbv7`) with `clang-cl` and `lld-link`. It fixes five
code-generation and linker defects that produce silently wrong ARM32 binaries, and four narrower
ones, and it **adds Windows SEH** — `__try` / `__except` / `__finally` — which no released clang
supports for this target. See the patch table in `RELEASE-NOTES.md`. **If you do not target ARM32
Windows, you do not need it.**

> ### This branch is the LLVM 18.1.8 line. There is a newer one.
> **[`main`](../../tree/main) now carries rt2 — LLVM 23.1.1 with six patches instead of ten**,
> because upstream fixed four of the ten rt1 had to carry, including the whole SEH backport. This
> branch is preserved exactly as it is; rt1, rt1.1 and rt1.2 releases will not change.
>
> **You do not have to move.** rt1.2's output is measurably *smaller* than rt2's on a real browser
> fleet, and it has more miles on it. Read *Should you move to rt2?* in `main`'s README before
> deciding.

Base is `llvmorg-18.1.8` (`3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff`).

---

## ⚠ If you are running rt1 1.0 or rt1.1, read this first

**Their documented install can produce a `clang-cl.exe` that crashes immediately and prints nothing
at all.** It affects both published releases. It surfaced on 2026-09-15, the first time anyone
assembled the package the way its own README says rather than running the drivers from the build
tree — not from an arm's-length third party, but from this project's own acceptance browser being
built against the shipped archive.

The official LLVM 18.1.8 package **bundles its own MSVC C++ runtime** in `bin/`, at version 14.29.
These drivers are built with the 14.44 toolset and import `MSVCP140.dll`. Windows resolves an
executable's own directory **before** the system directory, so a driver copied into that `bin/`
loads the stale 14.29 runtime sitting beside it and dies with an access violation (`0xC0000005`).

**If you are on rt1 or rt1.1**, delete these eight files from your installed `bin/` so every tool
resolves your system runtime instead:

```
msvcp140.dll  msvcp140_1.dll  msvcp140_2.dll  msvcp140_atomic_wait.dll
msvcp140_codecvt_ids.dll  vcruntime140.dll  vcruntime140_1.dll  concrt140.dll
```

**rt1.2 fixes this properly** by shipping the matching 14.44 redistributable and replacing those
eight files. Measured both directions before shipping: these drivers work beside it, **and stock
LLVM's own `clang-cl` still works beside it too** — the MSVC runtime is forward compatible within
14.x, which is what makes this a fix rather than a trade.

It was never caught in house because every test ran the drivers from the build tree, where no DLLs
sit beside them. The compiler worked in place and broke only when assembled the way the package
documents. There is now a gate that performs the documented install and then *runs* the result.

---

## What is new in rt1.2

- **`setjmp` / `longjmp` work on ARM32 (patch 0010, D42).** On Windows, `_setjmp` takes a second
  argument — the frame — which `longjmp` later hands to `RtlUnwindEx`. clang computed it with
  `llvm.sponentry` only for AArch64; 32-bit Arm fell through to `llvm.frameaddress(0)` and passed
  the **frame pointer**, which on ARM32 is `r11` and sits 8 bytes below the entry stack pointer.
  MSVC passes the entry stack pointer. Found on a device: a `longjmp` in a `clang-cl` build died
  **`STATUS_BAD_STACK` (`0xC0000028`)** where the MSVC build ran to completion.
- **The package installs correctly** — see the warning above.

Upstream has not fixed the `setjmp` defect in any clang this project has measured — **18.1.8, 21.1.8,
22.1.8, 23.1.0 and 23.1.1 all still emit `llvm.frameaddress`** for this target.

## Install

Install the official LLVM 18.1.8 win64 package, then copy the release archive's `bin/` and
`lib/clang/18/include/` over it.

> ⚠ **`bin/` contains eight Microsoft VC runtime DLLs as well as the nine drivers, and they must be
> copied with them.** That is what fixes the crash described above.

Every binary embeds the build commit `83c117cad0a9dee89e6daf6821c49156a3c562c0`:

```
findstr /M /C:"83c117cad0a9dee89e6daf6821c49156a3c562c0" <binary>     (cmd.exe)
grep -ac 83c117cad0a9dee89e6daf6821c49156a3c562c0 <binary>           (git-bash/WSL)
```

`findstr` prints the filename and exits 0; `grep -ac` prints 2.

**Check the other half too — rt1.1's and rt1 1.0's commits must be ABSENT:**

```
grep -ac 60876c5f8fad221756afd9bbd534377b7ff06571 <binary>           -> 0
grep -ac 7653a13d8d28189c7cef1401b934ec30d98ea353 <binary>           -> 0
```

That second check is not decoration. An early rt1.1 build carried rt1 1.0's commit by mistake, so
the presence test alone *passed* on it and reported it as the earlier release. Presence without
absence cannot tell two releases apart.

Both forms were run against all nine shipped binaries, and against **rt1.1** as a control, which
they correctly reject.

## What has been measured for rt1.2

- **It builds a real browser.** The full Varan tree (Pale Moon 34.3.1 / UXP 6.9.0) compiled and
  linked with rt1.2 from clean: **2,537 of 2,537 translation units, 19 of 19 PEs, zero errors**,
  every image ARMNT `0x01C4`. The browser launched on a Windows 10 ARM32 device.
- **What that does not establish:** it was **one device run, one page** — and **that run crashed**
  partway through, undiagnosed, with no dump captured. It is recorded because a release note that
  reports only the flattering half is not a release note.
- **No `longjmp` has been executed on hardware** with an rt1.2-built binary. The defect patch 0010
  fixes was measured on a device; the **fix** has been measured only in the compiler.
- **No object-by-object corpus gate was run for patch 0010.** rt1.1 earned that with 2,582 TUs
  compiled twice and compared; it was not repeated.

`RELEASE-NOTES.md` carries the full list.

## What is here

| | |
|---|---|
| `RELEASE-NOTES.md` | known differences from MSVC, known limitations, the porting checklist, provenance |
| `DISPOSITION-TABLE.md` | one verdict for **every** defect examined during this work — including the ones not fixed, and why |
| `patches/` | the ten patches as readable diffs |
| `runtime/` | the `__aeabi` divmod shim — source plus a prebuilt `.lib`/`.obj`, and a README saying exactly when you need it. It is opt-in, because adding it makes divide-by-zero trap |
| `stage/MODIFICATIONS.txt` | the Apache-2.0 §4(b) modification notice, and the package inventory. That is its path **in this repository**; inside the release archive it sits at the top level as `MODIFICATIONS.txt` |
| `tools/`, `scratch/` | the scanners, instruments and per-defect evidence the documents cite |

The `scratch/` paths look internal because they are: they are preserved exactly as the documents
cite them, so every citation resolves to a file you can open. A verdict whose instrument you cannot
inspect is an assertion, not evidence.

## Maintenance

**rt1.2 is a third frozen release, not the start of maintenance.** No rebases, no version bumps.
rt1.1's notes said there would be no rt1.2; rt1.2 exists because a `longjmp` was measured killing a
process on a device, not because a maintenance stream was started. The promise being kept is that
**no release changes after it is cut** — and none has.


## AI assistance

This toolchain's patches, measurements and documents were produced with substantial AI assistance,
reviewed and directed by a human, who is responsible for what is published here. Every measurement
quoted was executed, not predicted; where something was not measured it is listed as such rather
than omitted.

## Licence, and reporting a problem

Apache License v2.0 with LLVM Exceptions, as LLVM itself — the full text is `LICENSE.TXT` in the
release archive. The eight Microsoft VC runtime DLLs in `bin/` are Microsoft redistributables, are
not modified, and are not covered by that licence.

**Problems:** open an issue on this repository. This is a frozen release with no maintenance stream,
so a fix is not promised, but a reproducer is useful.
