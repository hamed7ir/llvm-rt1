# BATCH RT1-D38-1 — D38a settled: **DISCLOSE, no 0010**

2026-08-09. Compiler under test: `build/bin/clang-cl.exe` = `…18.1.8-rt1 (…7653a13d8…)`, the
shippable set.

---

## VERDICT

| | |
|---|---|
| **Is it a real clang defect?** | **YES.** MSVC differs on ARM32 — E1 |
| **Is it ARM32-specific?** | **YES** as far as MEASURED — `thumbv7` is the only target measured to diverge (E1.3); `i686`/`x86_64` were measured and agree, `aarch64` was never run against MSVC (see the E1 table row). Unlike D14, this is not an MS-ABI-wide story |
| **Carriers in the fleet?** | **ZERO**, across 2,582 TUs, with the floor confirmed firing — E2 |
| **Could a carrier hide in an array?** | **NO, structurally.** Arrays of a carrier are a loud compile error, so the build would already have failed — E3 |
| **Would a patch be a port?** | **NO — an invention.** The over-aligned-base family is a different mechanism on a different target, and its fix is gated away from ARM32 — E4 |
| **DISPOSITION** | **DISCLOSE. No patch. 0010 is NOT opened.** (0009 stays reserved for the D37 C-backport) |

---

## E1 — MSVC differs, so this is not WAI in the Bug-3 sense

Derived from **wrapper member offsets** only — `offsetof(W,m)` gives `alignof(V1)`,
`offsetof(W,t) − offsetof(W,m)` gives `sizeof(V1)`. Layout dumps were **not** used: MSVC's
`/d1reportAllClassLayout` prints `size(20)` on ARM where `sizeof` is **24**, which is the banked
methodology trap.

| target | clang (rt1) align/size | MSVC 14.16 align/size | |
|---|---|---|---|
| **thumbv7 / arm** | **8 / 20** | **8 / 24** | ✗ **DIVERGE** |
| i686 / x86 | 8 / 20 | 8 / 20 | ✓ agree |
| x86_64 / x64 | 8 / 24 | 8 / 24 | ✓ agree |
| aarch64 / arm64 | 8 / 24 | *(not run)* | — **not measured**; no MSVC ARM64 arm |

**This is the third independent derivation** and it agrees with the two already banked (direct
`sizeof`, and array stride via `sizeof(struct{V1 a[2];})`). MSVC identity captured:
`Microsoft (R) C/C++ Optimizing Compiler Version 19.16.27054 for ARM`.

---

## E2 — the carrier sweep: **0 carriers / 2,582 TUs**

**The invariant is internal**: a record with `sizeof % alignof != 0` is a carrier *by definition*.
No reference implementation and no MS-vs-Itanium diff, so `rt-layout-diff.py`'s structural
blindness does not apply and no MSVC arm is needed.

Method: `-Xclang -fdump-record-layouts` (**pass-1 only**; `-fdump-record-layouts-complete` crashes
the 18.1.8 base — MEASURED in T1, 177/185 TUs died). 8-way parallel over the command list that `scratch/F06/worker_ovr.sh` drives (a 4.7 MB generated
dump of per-TU command lines; regenerable from that harness and deliberately not banked).

```
chunks completed        : 8/8
carrier lines            : 0
```

### The floor, and why the zero means something

**A sweep that has never reported a carrier is not evidence.** Three arming steps, all run:

| arm | result |
|---|---|
| `d38scan.py --self-test` (synthetic) | **PASS** — reports the banked repro `V1 20/8`, silent on a clean control |
| end-to-end through the real compiler | **2 carriers** (`V1`, `V2`); the five control shapes `V3`/`V4`/`N1`/`P1`/`T1` correctly silent |
| **injected through the SWEEP'S OWN worker path** | **2 carrier lines** — this is the one that matters, because it exercises the exact pipeline that produced the zero |

### Coverage denominator — the other way a zero can lie

A zero is also produced by a sweep that silently compiled nothing. Measured on a 60-TU sample
through the same worker:

| | |
|---|---|
| TUs producing layout dumps | **59 / 60** |
| TUs producing zero dumps | 1 |
| records laid out in the sample | **25,870** |
| mean records per TU | **431** |

So the sweep is doing real work at roughly the expected scale (the banked corpus figure is 835,954
records). **The zero is an absence of carriers, not an absence of compilation.**

~~⚠ **STATED LIMIT.** This is the **pass-1** method…~~ **RETIRED 2026-08-09 by D38-COV — see below.**

---

## D38-COV — the stated limit is RETIRED. **Outcome A.**

The pass-1 limit existed because `-fdump-record-layouts-complete` crashes the 18.1.8 base. **rt1
carries 0008, which is the fix for exactly that crash**, so the full-coverage sweep is available on
rt1 and impossible on stock — and that asymmetry is itself the demonstration.

**The asymmetry, MEASURED on a real corpus TU (the single surviving stderr pair — `asym.sh` overwrites `/tmp/e_$a.txt` each iteration, so no per-TU log exists):**

| | stock 18.1.8 | rt1 `7653a13d8` (carries 0008) |
|---|---|---|
| `-fdump-record-layouts-complete` | **rc=1**, 57-line crash dump, *"PLEASE submit a bug report"* | **rc=0**, **zero stderr lines** |

This is a stronger demonstration of 0008 than its own lit tests: production TUs, full header
closures, not synthetic reductions. **It is worth a release-note line.**

**The full-coverage result:**

| | |
|---|---|
| TUs covered | **2,582 / 2,582** |
| records laid out | **7,018,478** |
| mean records per TU | **2,718** — vs pass-1's 431, a **6.3×** increase |
| TUs with a non-zero exit | **0** — rt1 survived every TU, so Outcome C is ruled out |
| TUs producing zero records | **0** — no silent failures |
| **D38a-class carriers** | **ZERO** |

⇒ **Outcome A.** The claim upgrades from *"no carrier among live records"* to **full
declared-record coverage across the corpus**: 7.0 M records, zero D38a carriers. D38a's DISCLOSE
disposition is unchanged and now rests on a much larger denominator.

> ⚠ **Correction to an interim figure of mine:** the smoke run reported 5,306 records/TU from the
> first 5 TUs, which are heavier than average. The corpus-wide mean is **2,718**. The 6.3× ratio
> above uses the corpus figure, not the smoke one.

### The four CARRIER lines are ONE record, and it is NOT D38a

All four occurrences (in `toolkit/components/downloads`, `widget/windows`, `xpcom/base`) are the
same record:

```
_STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE::(unnamed at winioctl.h:13430:5)   sizeof=1  alignof=4
```

An anonymous **union whose only members are flexible arrays** (`Lev1Depends[]`, `Lev2Depends[]`).
In C++ a complete object cannot have size 0, so it gets 1 byte, while alignment stays 4 from the
element type — hence `1 % 4 != 0`. **It cannot be D38a: D38a requires a virtual base, and a C union
in an SDK header has none.** My scanner's invariant is deliberately broader than D38a; this is the
first time that breadth has fired.

Three checks before calling it real, because the alternative was reporting a false positive:

| check | result |
|---|---|
| scanner soundness on `-complete` output | ran it over a 3,184-record dump verified by hand → **0 reported**; IRgen sections contain **no** `sizeof=` lines, so no format confusion |
| my first reconstruction | gave `[sizeof=4, align=4]` — **not** a carrier. The reconstruction was wrong, so it was discarded and the real header measured instead |
| C vs C++ mode | the same union is `4/4` in C and `1/4` in C++; the corpus TU is `.cpp` |

**Per the addendum's Outcome B this is recorded and does NOT reopen 0010** — pass-1 never saw it,
so nothing in the corpus lays it out, and E3's reasoning still governs.

⚠ **But chasing it surfaced a separate, larger finding that is not D38's** — see the new row **D39**
in the disposition table.

---

## E3 — the risk surface is narrower than it looks, and it is measured

**Structural bound: the fleet CANNOT contain an arrayed carrier.** Forming an array of one is a
loud refusal, so such a build would already have failed:

| construct on a carrier | rt1 result |
|---|---|
| `V1 arr[2];` | **REFUSED** — `error: size of array element of type 'V1' (20 bytes) isn't a multiple of its alignment (8 bytes)` |
| `p + 1`, `p[i]` on a `V1*` | **ACCEPTED** — no array type is formed, so nothing refuses it |
| `memcpy(q, p, sizeof(V1)*2)` | **ACCEPTED** |

**So the live risk was only ever non-array `sizeof` dependence** — pointer arithmetic, `memcpy` /
`memset` sizing, allocation sizing, serialization. With **zero carriers**, that surface is empty:
there is no carrier for any of those uses to apply to. Per E3.3 this is the *"zero carriers →
DISCLOSE, no 0010"* branch.

---

## E4 — a patch would be an INVENTION, not a port

The over-aligned-base lead is now **read**, not inferred.
[#210174](https://github.com/llvm/llvm-project/issues/210174) / PR
[#210461](https://github.com/llvm/llvm-project/issues/210461) → merged **`bd7bb26`, 2026-07-27**,
`main` only. Three independent mismatches:

1. **Mechanism** — theirs is tail-padding reuse for a base *following* an over-aligned base, via a
   new `getNonRequiredNVAlignment()`. D38's is the *final record size* not rounded to its own
   alignment.
2. **Trigger** — theirs needs an `alignas(16)` base. **D38's repro has no over-aligned base at
   all**; the derived class's alignment comes from an ordinary `double` member.
3. **Target** — the PR states the fix is *"gated to Arm64 only; Arm64EC and x64 follow the x64
   rule."* D38 diverges on **ARM32**, which that fix deliberately does not touch.

**Consequence:** unlike 0006 and 0008, there is no upstream fix to backport. 0010 would be ours to
invent, justify and defend forever — against a defect with **zero fleet carriers**. That is the
wrong side of the ledger.

**How it was searched** (standing caveat 3 — none of this proves absence): the four phrasings
recorded in `UPSTREAM-LEDGER.md`, plus direct reads of #210174, #210461, #95361, #53414, #48121.

---

## What ships instead

1. **DISCLOSE** in the release notes: on `thumbv7-*-windows-msvc`, a record with a virtual base
   whose virtual-base region ends on a non-multiple of the record's alignment gets a `sizeof` that
   is **4 bytes short of MSVC's**, and clang will **refuse to form an array of it**. The refusal is
   loud; there is no silent wrong code.
2. **Detection ships**, matching the Bug-3 framing already agreed — *rt1 cannot prevent this class,
   it makes it VISIBLE*: `scratch/D38/d38scan.py` + `worker38.sh`, both armed.
3. **H-D38** in `HANDOFF-TO-VARAN.md` runs the same armed sweep over the Varan tree, since this
   corpus is rt1's view of it and not the tree itself.
4. **Upstream draft**: a new issue, since E4 found no owning family. It should lead with the
   three-method agreement and the fact that clang's own dump prints the inconsistent pair.
