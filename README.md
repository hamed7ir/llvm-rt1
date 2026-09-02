# rt1.1 — a one-shot clang-cl / lld overlay for ARM32 Windows (LLVM 18.1.8)

rt1.1 is a small **binary overlay** onto the official LLVM 18.1.8 win64 package, for people
compiling C and C++ for **ARM32 Windows** (`thumbv7`) with `clang-cl` and `lld-link`. It fixes four
code-generation and linker defects that produce silently wrong ARM32 binaries, and four narrower
ones, and it **adds Windows SEH** — `__try` / `__except` / `__finally` — which no released clang
supports for this target. See the patch table in `RELEASE-NOTES.md`. **If you do not target ARM32
Windows, you do not need it.**

**rt1.1 is a SECOND FROZEN RELEASE, not the start of maintenance.** rt1 said it was released once,
with no rebases and no version bumps; that is still true of rt1, and it is true of rt1.1. This is a
second one-shot cut from the same frozen base, carrying one additional patch. There is no rt1.2
planned. **If you use rt1 and do not need `__try` on ARM32, you have no reason to move** — every
patch in rt1 is in rt1.1 unchanged, and the compiler produces byte-identical objects for code that
does not use SEH (measured over the whole 2,582-file corpus; see `RELEASE-NOTES.md`).

Base is `llvmorg-18.1.8` (`3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff`).

## Install

Install the official LLVM 18.1.8 win64 package, then copy the release archive's `bin/` and
`lib/clang/18/include/` over it. Nothing else in the installation is touched.

Every binary embeds the build commit `60876c5f8fad221756afd9bbd534377b7ff06571`:

```
findstr /M /C:"60876c5f8fad221756afd9bbd534377b7ff06571" <binary>     (cmd.exe)
grep -ac 60876c5f8fad221756afd9bbd534377b7ff06571 <binary>           (git-bash/WSL)
```

`findstr` prints the filename and exits 0; `grep -ac` prints 2.

**Check the other half too — rt1 1.0's commit must be ABSENT:**

```
findstr /M /C:"7653a13d8d28189c7cef1401b934ec30d98ea353" <binary>     -> no match
grep -ac 7653a13d8d28189c7cef1401b934ec30d98ea353 <binary>           -> 0
```

That second check is not decoration. The first rt1.1 build carried rt1 1.0's commit by mistake, so
the presence test alone *passed* on it and reported it as the earlier release. Presence without
absence cannot tell the two releases apart.

Both forms were run against all nine shipped binaries, and against **rt1 1.0** as a control, which
they correctly reject. `stage/MODIFICATIONS.txt` carries the full per-family recipe.

## What is here

| | |
|---|---|
| `RELEASE-NOTES.md` | known differences from MSVC, known limitations, the porting checklist, provenance |
| `DISPOSITION-TABLE.md` | one verdict for **every** defect examined during this work — including the ones not fixed, and why |
| `patches/` | the nine patches as readable diffs |
| `runtime/` | **the `__aeabi` divmod shim** — `aeabi-shim.c` plus a **prebuilt** `aeabi-shim.lib` / `.obj` for ARM32, and a README saying exactly when you need it. rt1 ships no compiler-rt builtins archive, and this is the mitigation; under rt1 1.0 it existed only outside the package, so porters knew about the gap but could not obtain the fix |
| `stage/MODIFICATIONS.txt` | the Apache-2.0 §4(b) modification notice, and the package inventory |
| `tools/`, `scratch/` | the scanners, instruments and per-defect evidence the two documents cite |

The `scratch/` paths look internal because they are: they are preserved exactly as the documents
cite them, so every citation in `DISPOSITION-TABLE.md` resolves to a file you can open. A verdict
whose instrument you cannot inspect is an assertion, not evidence.

## Rebuilding

`stage/MODIFICATIONS.txt` (SOURCE section) carries the configure command line that produced these
binaries and the two ways to obtain the source. One flag is not obvious and is required:
`-DLLVM_ENABLE_DIA_SDK=OFF`.

## Upstream

**One fix is now upstream.** Bug 2 — lld writing a local `__imp_` pointer to a Thumb function with
bit 0 clear — was submitted as [#215919](https://github.com/llvm/llvm-project/pull/215919) and
**merged 2026-08-27 as `bfaec6c07`**, touching `lld/COFF/Chunks.cpp`. It will ship in **LLVM 24**;
it is in no released version, which is why rt1.1 still carries patch 0002.

**The other three remain unfixed upstream** — Bug 1 (forwarded `musttail` registers), Bug 4
(CodeView tuple-register ICE) and defect #6 (musttail vararg + `va_start`). Drafts for those exist
outside this repository and have not been submitted. Issue numbers that appear in
`DISPOSITION-TABLE.md` other than #215919 are **other people's** existing upstream discussions,
cited as context.

## AI assistance

This work was **heavily AI-assisted and human-directed**. The direction, the standard of evidence,
the corrections and the validation are the author's, and the author is responsible for every patch
and every claim in this repository. The one upstream contribution made so far, `bfaec6c07`,
carries the disclosure LLVM's policy asks for as an `Assisted-by:` trailer on the landed commit.

## Licence

Apache License v2.0 with LLVM Exceptions, as LLVM itself. See `LICENSE.TXT` in the release
archive and the modification notice in `stage/MODIFICATIONS.txt`.
