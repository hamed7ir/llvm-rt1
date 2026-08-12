# `rt-layout-warn` — the single-compiler `-Wpadded` recipe

**What it is for.** You have a codebase you are porting to RT (Windows/ARM32, MS ABI) and you do
**not** have a second, Itanium-ABI build to diff against. This recipe turns rt1's own
`clang`/`clang-cl` into a one-compiler screen for the struct-layout trap described in
[`../upstream/README-porting-struct-layout.md`](../upstream/README-porting-struct-layout.md).

**Hard dependency, stated up front.** This works **only on rt1**, because of **patch 0006**
(`patches/0006-clang-ms-layout-padding-diagnostics.patch`), which wires `CheckFieldPadding` into
`MicrosoftRecordLayoutBuilder`. Without it that builder contains no diagnostic call at all, so
`-Wpadded` and `-Wpadded-bitfield` are **silently dead on every `*-windows-msvc` target** — MEASURED
here for **18.1.8** (§4); READ-IN-SOURCE for **19/20** from this project's upstream sweep; closed
upstream only in **clang 21**, which is the change patch 0006 backports (§4 row C1 measures clang 21
agreeing with rt1). §4 is this recipe's must-fail control.

---

## 1. The invocation

(shown wrapped for the page; each is **one line** in practice)

```
D:\repo\llvm-rt\build\bin\clang.exe  --target=thumbv7-unknown-windows-msvc
    -c -o <out>.o  -Wpadded -Wpadded-bitfield  <file>.cpp
```

clang-cl driver, same thing:

```
D:\repo\llvm-rt\build\bin\clang-cl.exe --target=thumbv7-unknown-windows-msvc
    -Wpadded -Wpadded-bitfield /c /Fo<out>.obj  <file>.cpp
```

Three requirements, each of which is load-bearing:

| requirement | why |
|---|---|
| **the rt1 binary** | patch 0006. Stock 18.1.8 is silent — §4. |
| **an `*-windows-msvc` triple** | the whole point is to see *MS* layout. Any `*-linux-gnu*` triple exercises the Itanium builder, which already warned in stock clang. |
| **`-c` (or `/c`), NOT `-fsyntax-only`** | **record layout is lazy.** See §3 — this is the one way to get a vacuous, always-green run. |

**Two Windows-path traps, both hit while writing this file:**

- `/Fo` takes **no colon**. `/Fopadprobe.obj` writes the object; `/Fo:padprobe.obj` exits 0 and writes
  **nothing**. Always `dir` / `Get-ChildItem` the object afterwards — a bare exit code proves nothing.
- Do not run the `clang-cl` form from **Git bash**: MSYS path conversion rewrites `/c` to `C:\...`, the
  driver never sees `/c`, and it tries to link. Warnings still print, so the run *looks* fine while the
  exit code is 1 for an unrelated reason. Use PowerShell for `clang-cl`, or the `clang.exe` + `-c` form
  above, which is MSYS-safe.

Add `-Werror=padded-bitfield` (and/or `-Werror=padded`) to make it a gate. MEASURED this session,
same probe, rt1, `thumbv7-unknown-windows-msvc` (caret/source lines trimmed):

```
padprobe.cpp:11:8: error: padding struct 'PoolHeaderPre' with 17 bits to align 'isNatural' [-Werror,-Wpadded-bitfield]
padprobe.cpp:12:8: error: padding struct 'PoolHeaderPre' with 31 bits to align 'ONES' [-Werror,-Wpadded-bitfield]
padprobe.cpp:9:8: error: padding size of 'PoolHeaderPre' with 2 bytes to alignment boundary [-Werror,-Wpadded]
padprobe.cpp:27:8: error: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Werror,-Wpadded]
4 errors generated.
exit=1
```

---

## 2. The probe: one struct that triggers, one that does not, one armed floor

Banked at **`D:\repo\llvm-rt\scratch\T11\padprobe.cpp`**. Shape (1) is the real UXP victim
`js::jit::PoolHeader` from `uxp/js/src/jit/arm/`.

The banked file is the authority; the block below is the same code with its header comment trimmed and
its rule statement sharpened from "differing declared *types*" to "differing declared *sizes*" per §5.
**Line numbers in the transcripts below refer to the banked file**, where `typedef unsigned int u32;`
is line 3.

```cpp
typedef unsigned int u32;

// (1) TRIGGERS under MS layout only.  Adjacent bit-fields with DIFFERING declared
// sizes: under the MS ABI `isNatural` (declared bool, 1 byte) cannot share the u32
// allocation unit, so the record is padded out and grows 4 -> 12 bytes.
// Under Itanium the same three fields pack into one 32-bit unit: no padding.
struct PoolHeaderPre {
  u32  size      : 15;
  bool isNatural : 1;
  u32  ONES      : 16;
};

// (2) DOES NOT TRIGGER anywhere.  Identical bit assignment, one uniform declared
// type.  Exactly 32 bits, no padding under either ABI.
struct PoolHeaderPost {
  u32 size      : 15;
  u32 isNatural : 1;
  u32 ONES      : 16;
};

// (3) ARMED FLOOR / must-fail control.  Plain trailing padding, ABI-neutral:
// 4*4 + 1 = 17 bytes rounded to 20.  Any live -Wpadded implementation must
// report this one, on every target.  If a run is silent about CtlAbiNeutral,
// the run proves nothing about the other two.
struct CtlAbiNeutral { u32 a; u32 b; u32 c; u32 d; unsigned char e; };

// A record is only laid out if it is actually USED.
void use(PoolHeaderPre, PoolHeaderPost, CtlAbiNeutral) {}
```

**Why struct (3) exists.** Without it, "the run printed nothing" is indistinguishable from "the flag
name was misspelled", "the file did not compile", "the records were never laid out", and "there is no
padding". `CtlAbiNeutral` pads identically under both ABIs, so it must appear in *every* green run. It
is the floor; a silent floor means the instrument is not armed and the run is discarded.

---

## 3. The gotcha that makes this recipe vacuous: `-fsyntax-only`

**MEASURED**, rt1, same file, same flags, only `-c` → `-fsyntax-only` changed:

```
> D:\repo\llvm-rt\build\bin\clang.exe --target=thumbv7-unknown-windows-msvc \
      -fsyntax-only -Wpadded -Wpadded-bitfield padprobe.cpp
exit=0
```

Nothing. Not one warning — **including the armed floor**. Clang lays a record out lazily; with
`-fsyntax-only` codegen never runs, so `void use(...)` never forces layout and the padding call sites
are never reached. A CI job written with `-fsyntax-only` is green forever and checks nothing. This is
exactly the "gate-vacuity" defect class.

**If you need a fast, no-codegen sweep** (e.g. header-only auditing), force layout in the source
instead of relying on codegen. MEASURED, rt1, `-fsyntax-only`, with
`static_assert(sizeof(X) != 0, "");` added per record
(banked: `D:\repo\llvm-rt\scratch\T11\padprobe_force.cpp`):

```
padprobe_force.cpp:7:8: warning: padding struct 'PoolHeaderPre' with 17 bits to align 'isNatural' [-Wpadded-bitfield]
padprobe_force.cpp:8:8: warning: padding struct 'PoolHeaderPre' with 31 bits to align 'ONES' [-Wpadded-bitfield]
padprobe_force.cpp:5:8: warning: padding size of 'PoolHeaderPre' with 2 bytes to alignment boundary [-Wpadded]
padprobe_force.cpp:17:8: warning: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Wpadded]
4 warnings generated.
exit=0
```

Floor present, trigger present, clean struct silent. Same file under stock clang / MS triple:
`exit=0`, no output; under stock clang / `armv7-unknown-linux-gnueabi`: the floor only, 1 warning.

A **definition of a global variable** of the type (`MixedBoolU32 g1;`) forces layout the same way, and
is what the banked `scratch/T10/bug3scope.cpp` and `scratch/T11/ruleprobe.cpp` probes use. MEASURED
(`scratch/T11/forcecheck.cpp`, four identical structs reached four different ways, rt1, MS triple,
`-fsyntax-only`): of `S1* p;`, `S2& r;`, `S3 g;`, `void f(S4);` — **only `S3` warns.** A pointer, a
reference and a function declaration never need a complete size, so they never lay the record out.

**Do NOT reach for `-Xclang -fdump-record-layouts-complete` to force layout.** MEASURED
(`RT1-WORKLOG.md` T1 pass 2, this repo): that flag **crashes** 18.1.8 on 177 of 185 real TUs
(`clang frontend command failed due to signal`), identically before and after patch 0006 — it is a
pre-existing base defect, fixed only in clang 21. Plain `-fdump-record-layouts` is fine, but it also
only dumps records that are actually used, so it does not solve the forcing problem either.

---

## 4. MUST-FAIL CONTROL — the measured stock-vs-rt1 pair

One variable at a time: **compiler** × **ABI**, same file, same flags, same session.

| # | compiler | triple | result |
|---|---|---|---|
| A1 | **rt1** `build\bin\clang.exe` | `thumbv7-unknown-windows-msvc` | **4 warnings** (2× `-Wpadded-bitfield` on `PoolHeaderPre`, 1× `-Wpadded` size on `PoolHeaderPre`, 1× floor) |
| A2 | **rt1** | `armv7-unknown-linux-gnueabi` | **1 warning** — floor only; `PoolHeaderPre` packs cleanly under Itanium |
| B1 | **stock 18.1.8** `C:\Program Files\LLVM\bin\clang.exe` | `thumbv7-unknown-windows-msvc` | **0 warnings — total silence, floor included** |
| B2 | **stock 18.1.8** | `armv7-unknown-linux-gnueabi` | **1 warning** — floor only |
| C1 | **stock clang 21.1.8** `clang21\pkg\bin\clang.exe` | `thumbv7-unknown-windows-msvc` | **4 warnings — identical text to A1** |

Row C1 is the upstream cross-check: patch 0006 is the clang-21 change backported, and clang 21.1.8
reports the same four findings, line for line, as rt1. Nothing about rt1's diagnostics is bespoke.

**"Every `*-windows-msvc` target" is measured, not extrapolated from `thumbv7`.** Same probe, same
flags, warning counts only (MEASURED this session):

| MS triple | stock 18.1.8 | rt1 |
|---|---|---|
| `i686-pc-windows-msvc` | 0 | 4 |
| `x86_64-pc-windows-msvc` | 0 | 4 |
| `aarch64-pc-windows-msvc` | 0 | 4 |
| `armv7-unknown-windows-msvc` | 0 | 4 |
| `thumbv7-unknown-windows-msvc` (rows A1/B1) | 0 | 4 |

Nothing about ARM32 or Thumb is involved on either side of this: the dead builder and its revival are
both **MS-ABI-wide**. See `../upstream/README-porting-struct-layout.md` for the layout rule itself,
which is likewise MS-ABI-wide and not UXP-specific.

Transcript, produced this session (PowerShell, `D:\repo\llvm-rt\scratch\T11`):

```
##### A1  rt1 / thumbv7-unknown-windows-msvc
padprobe.cpp:11:8: warning: padding struct 'PoolHeaderPre' with 17 bits to align 'isNatural' [-Wpadded-bitfield]
   11 |   bool isNatural : 1;
      |        ^
padprobe.cpp:12:8: warning: padding struct 'PoolHeaderPre' with 31 bits to align 'ONES' [-Wpadded-bitfield]
   12 |   u32  ONES      : 16;
      |        ^
padprobe.cpp:9:8: warning: padding size of 'PoolHeaderPre' with 2 bytes to alignment boundary [-Wpadded]
    9 | struct PoolHeaderPre {
      |        ^
padprobe.cpp:27:8: warning: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Wpadded]
   27 | struct CtlAbiNeutral { u32 a; u32 b; u32 c; u32 d; unsigned char e; };
      |        ^
4 warnings generated.
exit=0
##### A2  rt1 / armv7-unknown-linux-gnueabi
padprobe.cpp:27:8: warning: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Wpadded]
   27 | struct CtlAbiNeutral { u32 a; u32 b; u32 c; u32 d; unsigned char e; };
      |        ^
1 warning generated.
exit=0
##### B1  STOCK 18.1.8 / thumbv7-unknown-windows-msvc   <-- IDENTICAL invocation
exit=0
##### B2  STOCK 18.1.8 / armv7-unknown-linux-gnueabi
padprobe.cpp:27:8: warning: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Wpadded]
   27 | struct CtlAbiNeutral { u32 a; u32 b; u32 c; u32 d; unsigned char e; };
      |        ^
1 warning generated.
exit=0
##### objs
Name Length
---- ------
A1.o    693
A2.o    960
B1.o    693
B2.o    864
##### C1  STOCK clang 21.1.8 / thumbv7-unknown-windows-msvc
padprobe.cpp:11:8: warning: padding struct 'PoolHeaderPre' with 17 bits to align 'isNatural' [-Wpadded-bitfield]
padprobe.cpp:12:8: warning: padding struct 'PoolHeaderPre' with 31 bits to align 'ONES' [-Wpadded-bitfield]
padprobe.cpp:9:8: warning: padding size of 'PoolHeaderPre' with 2 bytes to alignment boundary [-Wpadded]
padprobe.cpp:27:8: warning: padding size of 'CtlAbiNeutral' with 3 bytes to alignment boundary [-Wpadded]
4 warnings generated.
exit=0        (c21.o present, 841 bytes)
```

**Read the cells:**

- **B1 vs B2** is the arming proof. Stock clang, same flags, same file — it warns under Itanium and is
  silent under MS. So the flag spellings are right, the file compiles, the records are laid out, and
  stock clang's padding machinery is alive. What is dead is specifically `MicrosoftRecordLayoutBuilder`.
- **A1 vs B1** is the patch-0006 dependency. Byte-for-byte the same command line; rt1 reports 4
  findings, stock reports 0. **This is the reason a user on stock clang sees nothing and must not
  conclude their code is clean.**
- **A1 vs A2** is the hazard itself: `PoolHeaderPre` warns under MS and not under Itanium, which is
  precisely the "compiles fine on Linux, wrong on RT" shape.
- **Every green cell contains the floor.** `CtlAbiNeutral` appears in A1, A2 and B2. B1's *absence* of
  the floor is the finding, not a broken run.

**Patch 0006 changes diagnostics only, never layout.** MEASURED: `A1.o` and `B1.o` are byte-identical.

```
> sha256sum A1.o B1.o
4a8e3ac1f191d79309425e0347c21c75e31ed48107f34d111a905e032fb77015 *A1.o
4a8e3ac1f191d79309425e0347c21c75e31ed48107f34d111a905e032fb77015 *B1.o
> cmp A1.o B1.o && echo "BYTE-IDENTICAL"
BYTE-IDENTICAL
```

**A trap in that check, and how to make it reproducible.** A COFF object carries a 4-byte
`TimeDateStamp` at **offset 4**, so a bare `cmp` of two objects only comes out clean when both
compiles landed in the *same second* — which is what happened to the banked `A1.o`/`B1.o` pair above.
Re-run the two commands a second apart and `cmp` reports `differ: char 5`, which is the timestamp and
**not** codegen. Do not read that as patch 0006 changing output. Add
`-mno-incremental-linker-compatible` (it writes a zero timestamp) and the identity is deterministic —
MEASURED this session, same probe, same flags:

```
> ...\clang.exe --target=thumbv7-unknown-windows-msvc -mno-incremental-linker-compatible \
      -c -o A1r.o -Wpadded -Wpadded-bitfield padprobe.cpp        # rt1
> ...\clang.exe --target=thumbv7-unknown-windows-msvc -mno-incremental-linker-compatible \
      -c -o B1r.o -Wpadded -Wpadded-bitfield padprobe.cpp        # STOCK 18.1.8
> sha256sum A1r.o B1r.o
6884e189381982849268f69a9cee811e6fb3a79ce21420d0df3778e6bfc58cb6 *A1r.o
6884e189381982849268f69a9cee811e6fb3a79ce21420d0df3778e6bfc58cb6 *B1r.o
> cmp A1r.o B1r.o && echo "BYTE-IDENTICAL"
BYTE-IDENTICAL
```

`cmp -l` on a timestamp-only difference lists **only** bytes inside offsets 4-7 (1-indexed 5-8).
Anything outside that window is a real difference and must be investigated.

---

## 5. Reading the output — what it does and does not prove

**The precise MS rule.** READ-IN-SOURCE, rt1 tree `llvm-project` @ `345ce564e`,
`clang/lib/AST/RecordLayoutBuilder.cpp:3040-3044` (the size comparison itself is on `:3044`):

```
  // Check to see if this bitfield fits into an existing allocation.  Note:
  // MSVC refuses to pack bitfields of formal types with different sizes
  // into the same allocation.
  if (!UseExternalLayout && !IsUnion && LastFieldIsNonZeroWidthBitfield &&
      CurrentBitfieldSize == Info.Size && Width <= RemainingBitsInField) {
```

The discriminator is a pure **size** comparison, not type identity and not signedness. MEASURED this
session with stock 18.1.8 (`scratch/T11/ruleprobe.cpp`, `-Xclang -fdump-record-layouts`):

| shape | `thumbv7-…-windows-msvc` | `armv7-…-linux-gnueabi` |
|---|---|---|
| `{int:5, unsigned:5}` — differing type, **same size** | `0:0-4`, `0:5-9`, sizeof **4** | `0:0-4`, `0:5-9`, sizeof **4** |
| `{signed char:3, unsigned char:3}` — differing type, same size | `0:0-2`, `0:3-5`, sizeof **1** | `0:0-2`, `0:3-5`, sizeof **1** |
| `{unsigned short:5, unsigned:5}` — **differing size** | `0:0-4`, **`4:0-4`**, sizeof **8** | `0:0-4`, `0:5-9`, sizeof **4** |
| `{bool:5, unsigned:5}` — **differing size** | `0:0-4`, **`4:0-4`**, sizeof **8** | `0:0-4`, `0:5-9`, sizeof **4** |

**`-Wpadded` over-reports.** It flags padding, not divergence, so it fires on shapes that are identical
under both ABIs. MEASURED (`scratch/T11/fnprobe.cpp` + `fnprobe_size.cpp`, ShowSize oracle — the
banked undefined-template technique from `scratch/FUZZ/repro_packdeclspec.cpp`, no layout dump
involved):

| shape | MS sizeof | Itanium sizeof | rt1 `-Wpadded*` on MS triple |
|---|---|---|---|
| `Fn1 {u16 a:16; u32 b:5;}` | **8** | **4** | 2 warnings — true positive |
| `Fn2 {u16 a:16; u32 b:32;}` | 8 | 8 | 1 warning — **false positive** (no divergence) |
| `Fn3 {bool a:8; u32 b:32;}` | 8 | 8 | 1 warning — **false positive** |

**Triage guidance, MEASURED.** The two flags are not equally informative. Same rt1 / MS-triple run over
`scratch/T11/ruleprobe.cpp`:

```
ruleprobe.cpp:4:8:  warning: padding size of 'SameSizeDiffType' with 22 bits to alignment boundary [-Wpadded]
ruleprobe.cpp:5:8:  warning: padding size of 'SameSizeDiffSign' with 2 bits to alignment boundary [-Wpadded]
ruleprobe.cpp:6:58: warning: padding struct 'DiffSize16_32' with 27 bits to align 'u' [-Wpadded-bitfield]
ruleprobe.cpp:6:8:  warning: padding size of 'DiffSize16_32' with 27 bits to alignment boundary [-Wpadded]
ruleprobe.cpp:7:58: warning: padding struct 'DiffSizeBool32' with 27 bits to align 'u' [-Wpadded-bitfield]
ruleprobe.cpp:7:8:  warning: padding size of 'DiffSizeBool32' with 27 bits to alignment boundary [-Wpadded]
6 warnings generated.
```

The two **ABI-divergent** shapes are the only two carrying **`-Wpadded-bitfield` on a named field**
(`… to align 'u'`); the two agreeing shapes carry only plain `-Wpadded` *size* notes about trailing
padding, which every dense struct has. So:

- **`-Wpadded-bitfield … to align '<field>'` is the high-signal line.** Triage those first.
- **`-Wpadded … padding size of … to alignment boundary` is background noise** on its own — trailing
  padding is normal and ABI-neutral. Keep the flag on (it is what caught `CtlAbiNeutral`, the floor),
  but do not chase every hit.
- `-Wpadded-bitfield` still over-reports (`Fn2`, `Fn3` above), so it is a shortlist, not a verdict.

So the honest characterisation:

- `-Wpadded` / `-Wpadded-bitfield` is a **screen**: cheap, single-compiler, and it fires on every
  divergent bit-field run found in this session's probes — but it also fires on benign ones. Triage
  the hits; do not treat the count as a defect count.
- This session's probes found **no** case where a measured MS-vs-Itanium divergence was silent under
  `-Wpadded`. That is a probe result, **not** a proof of completeness. `-Wpadded` never proves a
  record is portable.
- The **deciders** are, in order: `static_assert(sizeof(X) == N)` in the source (durable, survives
  every compiler), and [`rt-layout-diff.py`](rt-layout-diff.py) when a second ABI is available.

## 6. See also

- [`../upstream/README-porting-struct-layout.md`](../upstream/README-porting-struct-layout.md) — the
  hazard, the measured table, and the three source-repair rules.
- [`rt-layout-diff.py`](rt-layout-diff.py) — the two-ABI differ, and the *decider* this screen defers
  to. Interface (READ-IN-SOURCE from the tool; `--self-test` MEASURED this session, exit 0, and a
  divergent input MEASURED at exit 1): the file to audit is the **positional** argument;
  `--self-test` runs the armed self-test and exits; `--probe` is a **flag** adding the independent
  `ShowSize<>` sizeof/alignof oracle alongside the layout dump — it is *not* how you name the input;
  `--clang` selects the compiler binary; the arch-matched default triples are
  `armv7-unknown-windows-msvc` vs `armv7-unknown-linux-gnueabi`. Exit codes: 0 clean, 1 divergences
  found, 2 tool/usage error, 3 self-test failed. Run `--self-test` before trusting any clean run. Use
  it when you *can* build both sides; use this `-Wpadded` recipe when you cannot.
- `patches/0006-clang-ms-layout-padding-diagnostics.patch` — the patch this recipe depends on,
  including `clang/test/CodeGenCXX/warn-padded-microsoft.cpp`, its lit test.
