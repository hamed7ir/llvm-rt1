# rt1 — a one-shot clang-cl / lld overlay for ARM32 Windows (LLVM 18.1.8)

rt1 is a small **binary overlay** onto the official LLVM 18.1.8 win64 package, for people compiling
C and C++ for **ARM32 Windows** (`thumbv7`) with `clang-cl` and `lld-link`. It fixes four
code-generation and linker defects that produce silently wrong ARM32 binaries, and four narrower
ones — see the patch table in `RELEASE-NOTES.md`. **If you do not target ARM32 Windows, you do not
need it.**

It is **not a maintained fork**: released once, no rebases, no version bumps, no updates planned.
Base is `llvmorg-18.1.8` (`3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff`).

## Install

Install the official LLVM 18.1.8 win64 package, then copy the release archive's `bin/` and
`lib/clang/18/include/` over it. Nothing else in the installation is touched.

Every binary embeds the build commit `7653a13d8d28189c7cef1401b934ec30d98ea353`:

```
findstr /M /C:"7653a13d8d28189c7cef1401b934ec30d98ea353" <binary>     (cmd.exe)
grep -ac 7653a13d8d28189c7cef1401b934ec30d98ea353 <binary>           (git-bash/WSL)
```

`findstr` prints the filename and exits 0; `grep -ac` prints 2. Both were run against all nine
shipped binaries and against stock 18.1.8 as a control, which both correctly reject.
`stage/MODIFICATIONS.txt` carries the full per-family recipe.

## What is here

| | |
|---|---|
| `RELEASE-NOTES.md` | known differences from MSVC, known limitations, the porting checklist, provenance |
| `DISPOSITION-TABLE.md` | one verdict for **every** defect examined during this work — including the ones not fixed, and why |
| `patches/` | the eight patches as readable diffs |
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

**Nothing has been filed upstream.** Where `DISPOSITION-TABLE.md` says a filing is *prepared but
not yet submitted*, that is exact: drafts exist outside this repository and no issue or pull request
has been submitted. Issue numbers that do appear are **other people's** existing upstream
discussions, cited as context.

## AI assistance

This work was **heavily AI-assisted and human-directed**. The direction, the standard of evidence,
the corrections and the validation are the author's, and the author is responsible for every patch
and every claim in this repository. Upstream contributions, if and when they are made, will carry
disclosure per LLVM's policy.

## Licence

Apache License v2.0 with LLVM Exceptions, as LLVM itself. See `LICENSE.TXT` in the release
archive and the modification notice in `stage/MODIFICATIONS.txt`.
