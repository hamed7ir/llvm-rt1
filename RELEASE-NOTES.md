# rt1.1 — release notes

rt1.1 is a small **binary overlay** onto the official LLVM 18.1.8 win64 package, for people
**compiling C and C++ for ARM32 Windows** (`thumbv7`) with `clang-cl` and
`lld-link`. It fixes four code-generation and linker defects that produce silently wrong ARM32
binaries, and four narrower ones, and it **adds Windows SEH support for ARM32** — see the patch
table. If you do not target ARM32 Windows, you do not need it.

**To install:** install the official LLVM 18.1.8 win64 package, then copy this package's
`bin/` and `lib/clang/18/include/` over it. Nothing else in the installation is touched, and
`MODIFICATIONS.txt` tells you how to confirm the binaries you are holding are these ones.

## rt1.1 is a SECOND FROZEN RELEASE, not the start of maintenance

rt1 said it was released once, with no rebases and no version bumps. **That is still true of rt1,
and it is true of rt1.1 as well.** rt1.1 is not an update stream and does not make rt1's promise
retroactively false: it is a second one-shot release, cut from the same frozen `llvmorg-18.1.8`
base (`3b5b5c1ec`), carrying one additional patch. There is no rt1.2 planned, no rebase planned,
and no version bump planned.

If you are using rt1 and do not need `__try` on ARM32, **you have no reason to move.** Every patch
in rt1 is in rt1.1 unchanged, and the compiler produces identical objects for code that does not
use SEH — measured, not assumed; see *Verification status*.

Neither release is maintained. Both are archives.

---

## The patch set

**Nine patches, all accepted.**

| patch | fixes | origin |
|---|---|---|
| **0001** | Bug 5 — prologue over-allocates the frame by 8 bytes under the split R11/LR push | ours |
| **0002** | Bug 2 — lld writes a local `__imp_` pointer to a Thumb function with bit 0 clear | ours |
| **0003** | Bug 1 — forwarded `musttail` registers; vcall thunk uses an argument register as scratch | ours |
| **0004** | Bug 4 — CodeView ICE on a tuple-register `DBG_VALUE` | ours |
| **0005** | lit tests for the `this`-adjusting thunk cases | ours |
| **0006** | `-Wpadded` / `-Wpadded-bitfield` dead under the MS record layout builder | **PORT** from LLVM 21 |
| **0007** | musttail vararg forwarder that also calls `va_start` → backend fatal | ours |
| **0008** | crash under `-fdump-record-layouts-complete` | **PORT** of `e4882d83d77f` (LLVM 19) + 2 rt1 tests |
| **0009** | **NEW IN rt1.1** — Windows SEH (`__try` / `__except` / `__finally`) for ARM32 | **PORT** of `6c34ed7b3` (PR #184953, LLVM 21) |

---

# What is new in rt1.1

## Windows SEH works on ARM32 — and it does not, yet, in any released clang

`__try` / `__except` / `__finally` compile for `thumbv7-unknown-windows-msvc`. That is the whole
point of this release.

MEASURED 2026-08-31, one source file, four compilers, same target and flags:

| compiler | `__try` |
|---|---|
| **rt1.1** | **accepted** — object emitted |
| rt1 (the first release) | rejected: *"SEH '__try' is not supported on this target"* |
| clang **21.1.8** | rejected, same message |
| clang **22.1.8** | rejected, same message |

The gate is in the **front end**, and it is one condition. `TargetInfo::isSEHTrySupported()` allows
SEH on Windows for x86 and aarch64 only; patch 0009 adds `|| getTriple().isThumb()`. Read the
released headers and you can see it: `llvmorg-21.1.8` and `llvmorg-22.1.8` both have the two-target
form, upstream `main` has the three-target form.

**So this is a backport, not an invention.** Patch 0009 ports upstream `6c34ed7b3`
(*"[ARM] Add support for Windows SEH"*, PR #184953, 2026-05-18). That commit is on `main` and is
**not an ancestor of `llvmorg-22.1.8`** — the release branch had already diverged — so it has not
appeared in a released clang. If you want ARM32 SEH today, this package or a build of `main` are
the options.

**What was adapted, and why.** LLVM 18 declares the `cleanupret` SelectionDAG node with `SDTNone`
— zero operands — while `main` declares it with one. Upstream's `[(cleanupret bb)]` therefore fails
TableGen on an 18.1.8 tree before anything compiles. rt1 writes `[(cleanupret)]`, following the
spelling the same tree already uses for the two targets that support Windows SEH there
(`AArch64InstrInfo.td`, `X86InstrCompiler.td`). **This is version skew, not a defect in `main`**,
so there is nothing to report upstream; it is recorded as D41 in the disposition table so that the
next person to backport this patch does not rediscover it as a bug.

⚠ **SEH has compiled here; it has not been executed on hardware.** See *Hardware validation*.

## The `__aeabi` divmod shim now ships

rt1 shipped no `clang_rt.builtins` archive and no shim, which left porters knowing about the gap
but unable to obtain the fix. **The shim is now in the package, source and prebuilt**:

| file | size | what it is |
|---|---|---|
| `runtime/aeabi-shim.c` | 2,858 B | the source, so you can read and rebuild it |
| `runtime/aeabi-shim.lib` | 1,814 B | **prebuilt** — pass it to `lld-link`, no build step |
| `runtime/aeabi-shim.obj` | 1,466 B | the object, if you prefer it |
| `runtime/README-aeabi-shim.txt` | — | when it applies, and the one behavioural difference |

The prebuilt files were built by this package's own `clang-cl` for
`thumbv7-unknown-windows-msvc` at `-O1` with `-mno-incremental-linker-compatible`, so the COFF
timestamp is zero and they are reproducible. **They are the only ARM32 target binaries in the
package** — everything else here is the x64 host toolchain. `llvm-nm` shows exactly four defined
symbols (`__aeabi_idiv`, `__aeabi_idivmod`, `__aeabi_uidiv`, `__aeabi_uidivmod`) and two undefined
(`__rt_sdiv`, `__rt_udiv`, both from the MSVC ARM CRT).

**It is opt-in.** Nothing links it for you, and nothing should — adding it changes divide-by-zero
from whatever your code did before to a `__brkdiv0` trap. Add it when, and only when, the link
fails with those two undefined symbols.

The short version: **you almost certainly do not need it.** Ordinary `a / b` on this target lowers
to `__rt_sdiv` / `__rt_udiv`, which the MSVC ARM CRT ships — MEASURED, the only undefined symbols
in such an object. You need the shim only if your own source *names* `__aeabi_idivmod` or
`__aeabi_uidivmod`, as SpiderMonkey's soft-divide and wasm paths do.

**rt1.1 still ships no builtins archive, and that remains deliberate.** compiler-rt's
`__udivmodsi4` does not trap on divide-by-zero where MSVC's `__rt_*` helpers do; taking it would
trade a platform-matching trap for a silent wrong answer. Both CMake gates that would have blocked
building it actually move, so the gates were never the reason — the semantics are.

# Porting checklist for Windows RT / ARM32

**1. Thumb-2 only. A32 is device-lethal.** On Windows RT the kernel drops `CPSR.T` across
preemption into A32 code, so an A32 region dies non-deterministically. clang is not at fault — it
correctly emits `blx`. The consequence is structural: **an A32 JIT is impossible on this platform**,
not merely inadvisable.

**2. Machine type is `ARMNT`.** Target `thumbv7-unknown-windows-msvc`; link `-machine:arm`.

**3. Watch for `LNK4217` wherever `dllimport` lands on a locally defined symbol.** That warning
marks the case where the linker synthesises the `__imp_` pointer itself. Unpatched lld writes a
**function** pointer with bit 0 clear, so an indirect call through the slot requests ARM state and
dies. rt1 fixes this; if you build with stock lld, treat every LNK4217 on a function as a live
defect.

**4. The `__aeabi` divmod gap — but only if your source names those symbols.** compiler-rt ships
no `clang_rt.builtins` for a Windows thumb triple, so `__aeabi_idivmod` / `__aeabi_uidivmod` go
unresolved *when something references them*. Clang itself never emits them here: on
`thumbv7-windows-msvc` ordinary division lowers to `__rt_sdiv` / `__rt_udiv`. The same source at
the same `-mcpu` emits the `__aeabi_*` family only under an EABI triple. So this bites code that
names the helpers explicitly — in Varan, SpiderMonkey's wasm path takes the address of
`__aeabi_idivmod` — and a port that never names them will never see it.

- **The practical fix is a small shim** that forwards to the CRT's `__rt_sdiv` / `__rt_udiv`, plus
  a `long long` variant.
- **Divide-by-zero semantics — decided, and it matters.** MSVC 14.16's `__rt_udiv` and
  `__rt_sdiv` **TRAP** via `__brkdiv0`. compiler-rt's ARM `udivmodsi4` instead returns quotient 0
  and **never writes the remainder out-parameter**, so `__aeabi_uidivmod` reads an **uninitialised
  stack slot** — an indeterminate remainder, not zero.
- **rt1 does NOT ship a builtins archive.** A prototype exists in `scratch/` and is **gated off**
  by `scratch/W3/div0_check.py`, which fails it by design. If you build your own, either make the
  divide-by-zero path trap (matching the platform) or record deliberately that you accept
  non-trapping semantics — and in either case **write the remainder**, never leave it
  uninitialised.
- Upstream's `__MINGW32__` accommodation does **not** solve this: it renames the symbol and swaps
  argument order but still calls compiler-rt's own `__udivmodsi4`, carrying the identical defect.

**5. Layout audit recipe.** Before trusting struct layout across the clang-cl / MSVC boundary:
build with `-Wpadded -Wpadded-bitfield` (live again thanks to patch 0006), then, from the rt1
source repository (these scripts are not part of the binary overlay), run
`tools/rt-layout-diff.py` for MS-vs-Itanium divergence, `scratch/D38/d38scan.py` for
`sizeof % alignof != 0`, and `scratch/D39/famscan.py` for all-FAM unions. Every one of those has a
`--self-test` that must pass first — **a scanner that has never reported a known positive is not
evidence.**

---

# Known differences from MSVC

**The framing for this entire section: rt1 cannot prevent this class of difference — it makes it
VISIBLE.** Every item below is a place where clang-cl and MSVC 14.16 disagree, or where MSVC's own
behaviour is inconsistent. In each case a compiler-side "fix" would desync rt1's output from the
MSVC 14.16 CRT and from every MSVC-built ARM library you link against — which is worse than the
difference. So rt1 changes no layout. Patch 0006 ships **in the compiler**; the three scanners
below are published alongside these notes in the rt1 source repository, not inside the binary
overlay:

| detector | what it surfaces |
|---|---|
| **patch 0006** — `-Wpadded` / `-Wpadded-bitfield` revived under the MS record layout builder | padding insertions that MSVC reports as **C4820**; these diagnostics were silently dead under `-fms-compatibility` before |
| `tools/rt-layout-diff.py` | MS-vs-Itanium record layout divergence, arch-matched |
| `scratch/D38/d38scan.py` | records whose `sizeof` is not a multiple of their own `alignof` |
| `scratch/D39/famscan.py` | flexible-array-member-in-union types, the all-flexible-array-union family (D39) |

## Bitfield allocation units — working as intended, fix at the source

Under the MS ABI a bitfield whose **declared type differs** from the previous bitfield's starts a
**new allocation unit**. The Itanium ABI packs them together. So:

```cpp
struct S { unsigned a : 1; unsigned char b : 1; };   // MS: 2 units.  Itanium: 1.
```

**This is not a clang defect.** On the bitfield rule, clang-cl's output is
**byte-identical to MSVC 14.16 ARM `cl.exe`** across 12,000 generated shapes / 25,536 records:
**zero bitfield-straddling divergences**. (The corpus is not divergence-free overall — the sweep
surfaced **31 divergence records across 10 distinct shapes**, every one of them the
`__declspec(align)` case below, not this rule.)

**The fix is at the SOURCE and it is portable:** give every bitfield in a run the **same declared
type**, and the layout becomes identical under both ABIs. That is a one-line change per struct, it
needs no compiler flag, and it cannot desync you from anything.

**Do not "fix" this in the compiler.** A layout change here would make rt1's records disagree with
the 14.16 CRT and with every MSVC-built ARM library in your link.

## Virtual-base record size, `thumbv7` vs MSVC (disposition table: D38a)

For a record with a **virtual base** whose virtual-base region ends on a non-multiple of the
record's alignment:

| target | clang | MSVC 14.16 | |
|---|---|---|---|
| **`thumbv7`** | **align 8, sizeof 20** | **align 8, sizeof 24** | ✗ **differs** |
| `i686` | 8 / 20 | 8 / 20 | ✓ agree |
| `x86_64` | 8 / 24 | 8 / 24 | ✓ agree |
| `aarch64` | 8 / 24 | *not measured* | — |

**ARM32 is the only target that differs.** `i686` and `x86_64` were measured against MSVC
and agree; the `thumbv7` result was derived three independent ways (direct `sizeof`, array stride,
wrapper member offsets), all agreeing. ⚠ **`aarch64` shows clang's number only — no MSVC ARM64 arm
was run**, so that row is evidence neither of agreement nor of difference; it is recorded to show
clang itself is self-consistent there.

**The failure mode is LOUD, not silent (disposition table: D38b).** Forming an array of such a
record is a compile error:

```
error: size of array element of type 'V1' (20 bytes) isn't a multiple of its alignment (8 bytes)
```

so a build containing an arrayed carrier **cannot succeed**. What compiles silently is non-array
`sizeof` dependence — pointer arithmetic, `memcpy` sizing, allocation sizing.

The same 2,582-TU corpus was checked twice, by two instruments on opposite sides of the project
boundary:

| instrument | record-layout dumps examined | carriers |
|---|---|---|
| rt1's own sweep (all 2,582 TUs, full declared-record coverage) | **7,018,478** layouts (2,718/TU across overlapping header closures; not a distinct-record count) | **0** |
| the consumer-tree sweep (H-D38) — **129 of the same 2,582 TUs**, every 20th, deterministic | **25,916 distinct records** | **0** |

(distinct records saturate long before the TU list: 24,123 by TU 70, 25,916 by TU 129 — which is why
a 129-TU subset is not a 5% sample of the record universe)

Both sweeps had their floor **confirmed firing** — the scanner was shown reporting a known carrier
through the same pipeline before either zero was accepted.

## A union whose members are all flexible arrays (disposition table: D39)

| type | clang | MSVC 14.16 ARM |
|---|---|---|
| **`STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE`** (`winioctl.h`) | align 4, **sizeof 12** | align 4, **sizeof 76** |
| `CLUSPROP_SECURITY_DESCRIPTOR` (`ClusApi.h`) | 4 / 28 | 4 / 28 — **agree** |

**The trigger is precise, and narrower than "a flexible array member in a union":** it is a union
**every** member of which is a flexible array. `CLUSPROP_SECURITY_DESCRIPTOR` does **not** diverge
because its union also contains a **non-flexible** member (`SECURITY_DESCRIPTOR_RELATIVE sd`), and
that member sets the union's size.

**Decomposition** (element sizes are *identical* on both compilers, so the elements are not the
disagreement):

```
MSVC  76 = 8-byte header + one 68-byte LEV2_ENTRY   (reserves one element of the largest member)
clang 12 = 8-byte header + 4                        (all-FAM union sized as effectively empty)
```

**Consumer hazard.** This is an **IOCTL response struct**. Code that sizes a `DeviceIoControl`
buffer with `sizeof(STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE)` under clang-cl allocates **64 bytes
less** than a Microsoft-built driver expects to write. If you use this type, size the buffer
explicitly — do not use `sizeof`.

**Across the entire SDK + MSVC include set there are exactly two candidates and only this one
diverges.** On the consumer tree (H-D39, enumerator armed), there are **zero consumers** — nothing
uses the divergent type, so the hazard is documented rather than live.

## `__declspec(align(K))` below natural alignment inside `#pragma pack` (disposition table: D14)

When a type carries `__declspec(align(K))` with K **below** its natural alignment, and that type is
used as a **member inside a `#pragma pack(P)` region**, clang keeps the type's natural alignment.
MSVC emits **C4359** saying it will ignore the specifier — and then honours it.

**MSVC is self-inconsistent here**, so "match MSVC" is not obviously the right target, and this is
**upstream clang behaviour**, identical on stock 18.1.8, clang 21.1.8 and rt1 — it is not something
rt1 introduced or could sensibly change alone. Related upstream discussion:
[#63257](https://github.com/llvm/llvm-project/issues/63257) (i686 — so the divergence is
MS-ABI-wide, not ARM-specific).

**rt1 ships no patch for this, and that is now a measurement rather than a deferral.** The
consumer-tree check (H-ALIGN) ran to **Stage 2** and found **zero divergences** — the construct
that would carry the difference does not occur. Documented, not fixed.

---

# Known limitations

## `musttail` to a struct-returning function is refused on ARM32

A `musttail` call to a function that returns via a hidden `sret` pointer is a **hard error** on
ARM32:

```
fatal error: error in backend: failed to perform tail call elimination on a call site marked musttail
```

**This is a loud compile-time refusal. It is never silent wrong code** — which is why rt1 ships
without a fix rather than with a rushed one.

**Fixed upstream in LLVM 20, by a TWO-COMMIT stack**, both by Oliver Stannard (Arm), both landed
2024-10-25:

| commit | what it does |
|---|---|
| `c1eb790cd2f2` | *"[ARM] Tail-calls do not require caller and callee arguments to match"* — **+9 / −100 (net −91)** in `ARMISelLowering.cpp`; the real limit is only that the callee must not need more argument stack than the caller |
| `82e64721974b` | *"[ARM] Allow functions with sret returns to be tail-called"* — the one-line predicate change |

**rt1 carries neither.** The second was backported and **measured to give no improvement**: with it
alone, rt1 still fatals on exactly the realistic shapes (a `sret` forwarder with stack arguments),
identically to stock, while clang 22.1.8 compiles them. It was reverted rather than shipped as a
fix that fixes nothing.

**Workaround:** replace the struct return with an **explicit out-pointer in `r0`**, which is
register-identical at the ABI level.

## LTO is untested

rt1's `lld` **does** carry the codegen fixes, but **no oracle has ever run through the LTO code
generator**. If you link with `lld-link` under LTO you are on ground rt1 has not measured. This is
a gap in rt1's validation, not a known failure.

## Five auxiliary binaries ship unpatched

`clang-check`, `clang-repl`, `clang-scan-deps`, `clang-linker-wrapper` and `llvm-dwp` are **not
rebuilt** in this overlay. MEASURED by a byte screen over all 62 executables of the stock package
(armed: the ARM pass-name strings are absent from `clang-format`, `llvm-strings`, `llvm-objdump`,
`clangd`, `clang-tidy`, `llvm-mca`, `llvm-ml`), these five are the only unreplaced binaries that
link the ARM backend, so the defect code is present in them. They are 0-invocation in the target
workflow — if you invoke them, you are using stock 18.1.8 behaviour.

## Build configuration

The configure command line is in `stage/MODIFICATIONS.txt` (SOURCE section). It reproduces this build from an
empty build directory, and already carries `-DLLVM_ENABLE_DIA_SDK=OFF` explicitly. Host toolset:
vs22buildtools 14.44 (MSVC 14.16 cannot host LLVM 18 — it remains the **target** environment rt1's
output links against, not the host compiler). Generator: ninja 1.13.2.

One flag is not obvious: **`-DLLVM_ENABLE_DIA_SDK=OFF` is required.** LLVM defaults it to whether
the host has the MSVC DIA SDK; this host does (confirmed 2026-08-11), and LLVM's DIA code needs
ATL — a separate VS component that was absent. Without the flag a clean configure enables the DIA code that needs ATL; that
configuration was never built here, so the failure mode is expected rather than observed. No `CMAKE_MSVC_RUNTIME_LIBRARY` override is set, so the MSVC runtime defaults to
`/MD`.

The product target list is `clang clang-resource-headers lld opt llc llvm-reduce FileCheck count
not`. To run the test suite you additionally need seven targets beyond that:

```
llvm-config  llvm-readobj  llvm-objdump  yaml2obj  llvm-mc  llvm-nm  split-file
```

⚠ **Measured on this tree that adds +81 build edges; the project's own earlier record says +82.**
The discrepancy is unresolved and is reported rather than reconciled — treat 82 as the budget.

`LLVM_VERSION_SUFFIX=-rt1` is what puts `-rt1` in the version string; `CLANG_VENDOR` and
`LLD_VENDOR` are both set to `Varan` (the vendor prefix). Neither embeds the commit — that comes
from the checkout LLVM is built from. `lld` strips the suffix, so only the vendor shows on an lld
driver; verify an lld binary's commit by searching its bytes directly — `findstr /M
/C:"7653a13d8…" <binary>` in `cmd.exe` (prints the filename, exits 0) or `grep -ac
7653a13d8… <binary>` in git-bash (prints a nonzero count — **2** on every binary here, the commit
being stored twice). **9 of 9 pass both** (checked 2026-08-11), and both correctly **reject** the
stock 18.1.8 `clang.exe` used as a control, so neither command passes whatever it is handed. The
same file carries the commit-verification pair too. Drop-in preconditions for the overlay: no
LLVM DLLs, resource headers at `lib/clang/18`.

---

# Provenance and honesty

## Which patches are ports, and which are ours

| patch | origin |
|---|---|
| **0006** — `-Wpadded` under the MS record layout builder | **PORT** of upstream's LLVM 21 implementation, structurally identical at the same call sites |
| **0008** — guard `RecordDecl::completeDefinition()` | **PORT**, verbatim, of upstream `e4882d83d77f` (first shipped **LLVM 19**, never backported to 18.x) — including upstream's own comment block and both of its test files, plus **two rt1-authored tests, which are ours** (`dump-complete-invalid-field.cpp`, `dump-complete-uninstantiable.cpp`) |
| **0002** — lld local-import Thumb bit | **ours**, and **now upstream**: submitted as PR #215919 and **merged 2026-08-27 as `bfaec6c07`**, touching `lld/COFF/Chunks.cpp`. It will ship in **LLVM 24** and is in no released version, which is why rt1.1 still carries the patch |
| **0009** — Windows SEH for ARM32 | **PORT** of upstream `6c34ed7b3` (PR #184953), adapted for LLVM 18's `cleanupret` arity — see D41 in the disposition table. That commit is on `main` and is **not** an ancestor of `llvmorg-22.1.8`, so it has shipped in no released clang |
| 0001, 0003, 0004, 0005, 0007 | **ours** — authored here, with upstream drafts written but **not filed**. Bug 1 (forwarded `musttail` registers), Bug 4 (CodeView tuple-register ICE) and defect #6 (musttail vararg + `va_start`) all **remain unfixed upstream** |

**Upstream is owed nothing for the fixes in 0006 and 0008** — they are upstream's own, carried back
to a branch that never received them. 0008's two rt1-authored tests are ours and are offered, not
owed. A reader counting patches against filings should not read those two as missing filings.

## 0008's payoff

0008 fixes a crash under `-fdump-record-layouts-complete`, a `-cc1`-only flag that cannot bite a
production build. That bounds its severity — but it buys rt1 a capability stock 18.1.8 does not
have. On a real corpus translation unit, one pair of stderr captures survives:

| | stock 18.1.8 | rt1 |
|---|---|---|
| `-fdump-record-layouts-complete` | **rc=1**, 57-line crash dump, *"PLEASE submit a bug report"* | **rc=0**, **clean, zero stderr** |

Evidence banked in-repo: `scratch/D38/evidence/0008-asym-stock-stderr.txt` (57 lines) and
`0008-asym-rt1-stderr.txt` (0 bytes).

**Consequence: rt1 can audit record layouts at FULL DECLARED-RECORD COVERAGE where stock 18
crashes.** That is what made the 7,018,478-record virtual-base-record-size sweep possible at all
(disposition table: D38a) — stock 18.1.8 crashes on this input class (above). The sweep harness
records a failing TU and continues (`scratch/F06/worker_ovr.sh`'s FIRSTERR error-logging block: it
greps the stderr for the error, logs it, and moves to the next TU), so a stock run would not have
stopped — it would have returned a corpus with the crashed TUs contributing zero records, which is
not full declared-record coverage. On rt1 the same sweep recorded **zero** TUs with a non-zero exit
and **zero** silent TUs. This record does not establish which translation unit in a full sweep
would trigger the crash first, only that a stock run would not have reached full declared-record
coverage.

## The disposition table ships as the honesty section

Every defect examined during this work — the 38-row master table plus four items opened after it,
opened as the work found them — ships with its evidence, and the master table's rows each carry a
verdict. One of the four additional items is a tooling defect: `gate-thunks.py` reads too few bytes
to tell the fix from the bug (disposition table: D40). It is deferred, not fixed — the door is to
widen the compare to four bytes and add a floor that fails on a synthetic `f8d0 1000`. This
includes the ones that turned out to be NOT-A-BUG, the ones that are platform hazards rather than
compiler defects, the tooling defects found in rt1's own instruments, and the rows still open.
**Nothing is omitted because it
was inconvenient.**

Where a verdict rests on an instrument, the instrument's arming is stated too — several of this
project's findings were corrections to its *own* measurements, and those corrections are in the
table beside the results they replaced.

## AI assistance

This work was **heavily AI-assisted and human-directed**. The submitter is responsible for every
patch and every claim. Upstream contributions carry disclosure per LLVM's developer policy.

⚠ **Re-check the exact policy wording immediately before opening the PRs, not now** — it moved
recently (the Developer Policy now redirects to a separate AI Tool Use Policy) and the notes must
not encode a stale requirement.

## Verification status

### rt1.1's own gate: the whole Varan corpus, compiled twice, compared object by object

**2,582 of 2,582 translation units. 2,581 sha256-identical. One difference, explained. Zero
skipped. 38 of 38 subtrees.**

Every TU of the Varan browser corpus was compiled by **rt1 1.0** and by **rt1.1**, same flags, same
order, debug info off, and the resulting objects compared by sha256. The point is narrow and it is
the one that matters for a second release: **patch 0009 changes nothing for code that does not use
SEH.** That is what allows rt1.1 to inherit rt1's device validation instead of requiring a new
hardware trip for the patches that were already accepted.

The single difference is `js/src/jit/VaranFaultReporter.cpp`, which embeds `__DATE__` and `__TIME__`
in a string literal. It is not codegen: the *same* compiler run twice, twenty seconds apart, differs
in the same bytes. Exactly one source file in the corpus does this.

The comparison is armed rather than merely quiet. Run against stock LLVM 18.1.8 instead of rt1.1 —
two compilers that genuinely differ — the same harness reports **2 differing objects out of 40**, in
libffi. So "identical" is an absence of difference, not an inability to see one.

**What this does not cover: SEH itself.** No `__try` block in this corpus reaches a device in this
measurement — the corpus gate compares objects, not behaviour. **SEH was validated separately, on
hardware:** see *SEH on real hardware*, below.

### SEH on real hardware — Tegra 3, Windows 10 build 15035, 2026-09-02

`__try` / `__except` / `__finally` were executed on an actual ARM32 device and compared against
**MSVC 14.16 as the reference implementation**, same source, same four modes.

**Every mode passed in both toolchains, and every recorded field is identical.** A diff of the two
arms' output — excluding only the two lines that identify which compiler built each binary —
returns nothing:

| mode | MSVC 14.16 | rt1.1 |
|---|---|---|
| `except`  | PASS | PASS |
| `finally` | PASS | PASS |
| `nested`  | PASS | PASS |

`nested` is the one that matters: the inner filter declines and the **outer** handler catches, which
is real stack unwinding rather than a single-frame shortcut.

**The must-fail control ran first and died in both arms**, exit `0xC0000005`, as it must — a filter
that declines with nothing else to handle the fault has to kill the process. Had it survived, the
probe could not detect a dispatch failure and every other result would have been discarded. The
run script enforces that itself and stops.

Both binaries were hash-verified on the device before anything ran, and each carries its own build
identity into its results, so the two columns above are provably from two different compilers.

Full record: `scratch/A32M/P5-RESULTS.md`, with the raw device output at
`scratch/A32M/results/trip-5-p5/`. The readings were fixed in writing **before** the trip.

### rt1's device trip

The device trip returned PASS on 2026-08-09. All eight patches are ACCEPTED; the provisional
tags are resolved. The three entries that were blocked — the `declspec(align)` case, the
virtual-base record size, and the all-flexible-array union (D14, D38a, D39) — now carry their
measured counts. Hardware validation, below, records the device trip.

Six mechanical passes and one human end-to-end read were applied to this document.
`RT1-NOTES-VERIFY.md` records the sequence: pass 1 (92 TRACED / 17 WRONG / 3 UNTRACEABLE), a
re-verify of the applied corrections (22 / 7 — two of those seven were defects in the correction
record itself, claiming edits never made), a full-tracked-corpus third pass (265 / 45 / 1), then
rounds 4, 5 and 6 over the corrections each previous round produced (33, 36 and 25 corrections
applied; 0 missed anchors in every round after the first). Round 6 closed at 4 consumer-facing
findings, all fixed.

A human end-to-end read then found six more, none of which any mechanical pass had caught —
including the one that mattered most: this document claimed the build host had no MSVC DIA SDK
and therefore needed no flag to reach `LLVM_ENABLE_DIA_SDK=OFF`. The SDK is present. The published
configure line did not reproduce this release from a clean build directory, and now does — see
Build configuration, in Known limitations.

A mechanical sweep over the lines that read changed found 0 surviving superseded values and 0
absent replacements, with the check itself confirmed able to catch a planted error.

**What remains unverified, precisely:** the prose written for those six corrections has had the
mechanical sweep but not a second human read. Nothing else about this document is outstanding.

---

# Hardware validation

The toolchain was not accepted on the strength of unit tests. It was accepted because the browser
it exists for was **rebuilt with it and run on the silicon the bugs were lethal on**.

## The runtime self-check, on device

Patch **0007** shipped under a pre-agreed rule: green on hardware or it drops. The rule was written
before the run so the result could not be argued afterwards.

| binary | result |
|---|---|
| `vafwd-arm32.exe` | **11/11 cases PASS, exit 0** |
| `vafwd-arm32-mustfail.exe` (the armed floor) | failed **case 7 and only case 7**, exit 1 |

The must-fail companion is what makes the green mean anything: it is the same program with one
expectation perturbed, so a run where *both* binaries pass would prove the harness blind rather
than the compiler correct. **It failed exactly where it was built to fail.**

## Two post-link scaffolds retired, each replaced by a compiler fix

These are counts measured **statically on the linked fleet** that then ran on device — not counts
of dereferences observed at runtime:

| scaffold, now removed | replaced by | measured on the shipped build |
|---|---|---|
| a COMDAT object overriding vcall thunks to use `r12` | **patch 0003** | **178/178** `$B` thunks natively emit `f8d0 c000` — established by reading **all four bytes** of each thunk, not by the shipping gate, which compares only the first halfword (see D40 / H-GATE); **4,334 thunks / 4 families / 19 PEs / 0 carriers** |
| a post-link Thumb-bit fixer script | **patch 0002** | **233,046** local `.text` pointers, **all odd, zero even — with the fixer never run** |

What that row is and is not: **233,046 is the number of slots that exist and are correct**, not the
number that were ever broken. On the pre-rt1 fleet, the post-link fixer actually repaired **100**
pointers (nss3.dll 90, xul.dll 10); the other 17 of 19 PEs reported nothing to fix
(`scratch/D38/evidence/build-nav-fixup.log`, banked byte-identical from the pre-rt1 Varan build;
sha256 `ee49c3874f727d0063d6fbce6f7792c1285c1b2600569ee9b2d4baa18fd5af49`). The value of patch 0002
is that the correctness is now structural — the linker writes the bit — rather than dependent on a
post-link script being run correctly every time.

## The fleet build and the gates

Full rebuild with both scaffolds removed: **rc=0, 2,585 objects, 0 errors** — 19 our-built PEs, 21
scanned in total (the other two are the prebuilt `d3dcompiler_47.dll` and an i386 `helper.exe`).
All standing gates **PASS, exit 0**, plus three spot oracles. Staged payload: **3,612 files,
checksums verify.**

## Browser smoke — recorded as what it is

The browser was launched on device and exercised by hand: **no crash, no new problems,
indistinguishable from the pre-rt1 build.**

**This is an operator summary, not a measurement.** It is not a benchmark, not a test suite, and
not a claim of equivalence — it is a competent human using the browser and reporting that nothing
broke. It belongs here because a toolchain change that passed every gate and still made the
product visibly worse would be a failure; it does **not** belong in any argument that requires a
number.

---

## What is still open — and none of it blocks this release

| item | state |
|---|---|
| **verification pass over this document** | **DONE.** Six mechanical passes (92/17/3 · 22/7 · 265/45/1 · then rounds 4–6, 94 further corrections, 0 missed anchors) plus a human end-to-end read that found six more — see Verification status, in Provenance and honesty. A sweep over the changed lines returns 0 surviving superseded values and 0 absent replacements, floor armed. Residue, stated exactly: the prose written for those last six corrections has had the sweep but not a second human read |
| **`musttail`→`sret` tail call** (D37) | refused on ARM32; fixed upstream in LLVM 20 by a two-commit stack rt1 carries neither half of. **This release will not carry it** — the door is recorded for a future one-off only, and it opens on a byte-identical fleet rebuild plus a runtime acceptance (see the disposition table) |
| **LTO** | rt1's `lld` carries the codegen fixes; nobody has run them under LTO |
| **five auxiliary binaries** | ship unpatched, 0-invocation |
| **upstream filings** | drafts complete; filing is the submitter's action |
