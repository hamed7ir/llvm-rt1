# Disposition table

Every defect, hazard and limitation found across the clang-cl/lld `thumbv7-windows-msvc` campaign,
with **exactly one verdict each**. Built by walking `CLANG-CL-THUMBV7-BUGS.md` end to end (canonical
copy in the Varan catalog's tree, `CLANG-CL-THUMBV7-BUGS.md`, 866 lines, read-only; working copy
`CLANG-CL-THUMBV7-BUGS.md.copy` in this project's working tree) and then adding everything the rt1
campaign found that the catalog does not carry.

**Verdict vocabulary (one per row, no exceptions):**
`FIXED-BY-PATCH-N` · `NOT-A-BUG` · `OS/PLATFORM-HAZARD` · `OPEN` · `ARMED — DEMONSTRATION OWED`
· `CLOSED`
*(The last two are 2026-08-10 additions, each used on named rows only: `ARMED — DEMONSTRATION
OWED` on D26 and D27 (2 rows) — a floor that is armed in the tooling but has never been shown to
fire in both directions is neither OPEN nor CLOSED; `CLOSED` on D34 (1 row) — a packaging TODO
that turned out to already be done, not a compiler-defect verdict, so it does not fit
FIXED-BY-PATCH-N or NOT-A-BUG either.)*

**Rule applied:** anything without a settled verdict is **OPEN**, never omitted. Where a verdict was
uncertain, OPEN was chosen over a confident guess.

**THE D03 RULE — a row whose verdict depends on an UNMEASURED PATH is `OPEN`, not `FIXED`.**
Bug 1 was recorded `FIXED-BY-PATCH-0003` on the strength of an oracle covering the **register**
path. A *second* emission site — the tail-call **stack-argument shuffle** — was noted but **never
A/B tested**; the only claim about it was INFERRED. That is row **D03**, and it is the precedent
this rule is named for. A patch that demonstrably fixes the path it was measured on says nothing
about a path nobody measured, and the table must not let the first imply the second. Applies
equally to `NOT-A-BUG`: an absence of symptoms is not a verdict unless the *mechanism* is named.
*(Status note, 2026-08-05: D03 has since been measured and closed **NOT-A-BUG (mechanism named)**
— see the D03 detail block. The rule keeps its name and its force; the row that motivated it was
discharged the only way the rule allows, by measuring the path.)*

**⚠ NUMBERING COLLISION — read this before citing anything.** Defect numbers and patch numbers are
different sequences and they overlap confusingly:

| defect | fixed by | note |
|---|---|---|
| **#6** (musttail vararg + `va_start` fatal) | **patch 0007** | unfixed upstream, including on `main` |
| **#7** (`-Wpadded` dead under MS layout) | **patch 0006** | fixed in LLVM 21; 0006 is that backport |

They are off by one against each other. Every row below that concerns either one carries **both**
identifiers explicitly; never cite a bare "7" or "0007".

**⚠ TWO PATCHES ARE BACKPORTS *FROM* UPSTREAM AND ARE NEVER SENT UPSTREAM.** Stated here as well
as in an upstream filing prepared but **NOT YET FILED** §W5c, because a reader who counts *8 patches, 6 drafts* will
otherwise conclude two filings were forgotten. They were not — upstream is not owed them:

| patch | what it is | upstream owes us nothing because |
|---|---|---|
| **0006** | LLVM 21's `-Wpadded`/`-Wpadded-bitfield` wiring in `MicrosoftRecordLayoutBuilder`, structurally identical at the same call sites | it is **upstream's own fix**, already released in 21 |
| **0008** | `e4882d83d77f` (2024-03-04), first shipped in **LLVM 19**, never backported to 18.x | it is **upstream's own fix**, already released in 19 |

Every *other* patch in the series has an upstream track under working rule 12 — a confirmed defect gets both an rt1 patch and an upstream draft, as additive tracks, never alternatives.

**Evidence labels:** `[measured]` = produced by running something here, this session ·
`[read-in-source]` = read directly out of the named tree, this session · otherwise the banked
report + section is named and the label it carries there is preserved.

---

## State this table was built against (all `[measured]`)

> ⚠ **This section describes the rt1 1.0 era and is left as the record of it.** It is dated
> 2026-08-09/10 and every figure in it was true then. **If you are holding the rt1.1 package, three
> of its facts have moved on**, and they are stated here rather than silently rewritten:
>
> | this section says | rt1.1 |
> |---|---|
> | tree at `7653a13d8`, 9 commits ahead | **`60876c5f8`**, 10 commits ahead — patch 0009 added |
> | `patches/` = 0001–0008, 22 files, +1,239/−32 | **0001–0009**, 38 files, **+2,312/−123** |
> | `build/bin/clang.exe` at `7653a13d8` | rebuilt: **`f35413080e020531…`**, reporting `60876c5f8` |
>
> The rows below were not re-measured against rt1.1. Their *verdicts* were re-examined and stand;
> their *era* is 1.0. Where a row's evidence names a commit or a binary hash, read it as a record of
> what was measured then, not as a claim about the package you are holding.

| fact | measurement |
|---|---|
| tree *(as of 2026-08-09; hash re-verified 2026-08-10)* | this project's working tree checkout of `llvm-project` @ **`7653a13d8`**, **9 commits** ahead of `3b5b5c1ec`, `git status --porcelain` empty |
| commits | `7653a13d8` 0008 (was `bed948385` before a later amend) · `a20eeb750` 0007 · `345ce564e` 0006 · `3afb49879` 0003-fix · `386331553` 0005 · `17fd79072` 0004 · `a1f390894` 0003 · `e24a313bc` 0002 · `07030b2b1` 0001 · base `3b5b5c1ec` |
| patches present | `patches/` = **0001–0008**. Series verified **cumulatively** against a fresh `3b5b5c1ec` worktree: **8/8 APPLIED**, 22 files, **+1,239/−32**, with a must-fail control (re-applying 0008 onto the patched tree fails) |
| ⚠ binary vs tree | `build/bin/clang.exe` is at **`7653a13d8`** — it **CONTAINS** 0008 (rebuilt; MEASURED 2026-08-10, `--version` prints `…7653a13d8d28189c7cef1401b934ec30d98ea353)`). The STOP condition that held the rebuild is CLEARED |
| upstream drafts present | `upstream/` = `ISSUE-bug5-backport.md`, `ISSUE-bug1-musttail-forwarded-regs.md`, `ISSUE-bug2-lld-thumb-bit.md`, `COMMENT-bug4-issue-64278.md`, `ISSUE-6-musttail-vararg-vastart.md`, `README-known-limitations.md`, `README-porting-struct-layout.md`, `README.md` |
| compilers used | the stock, unpatched reference install = `clang version 18.1.8` · rt1's build output = `Varan clang version 18.1.8-rt1 (…7653a13d8d28189c7cef1401b934ec30d98ea353)` (the table's measurements pre-dating the 2026-08-09 rebuild were taken at `345ce564ec…`, the 0006 tip — noted where they are cited) · the banked reference package = `clang version 21.1.8` |

---

## D4 — THE TRIAGE (2026-08-09). Every row in exactly one bucket, none omitted

**This is the release's honesty section. It ships as written.**

Bucket meanings, fixed once so they cannot drift:

| bucket | means |
|---|---|
| **FIX-NOW** | rt1 owes a code change before release. **No row may sit here without a NAMED ORACLE** — an instrument that has been shown to produce the wrong answer on the wrong input |
| **DISCLOSE** | real, measured, and rt1 will **not** change behaviour. It ships documented. This is a decision, not a shrug |
| **DEFER-DOOR** | not closed, and the *door* is named: the specific measurement or event that would close it. A door without a named oracle is not a door, it is a wish |
| **USER-ACTION** | the action belongs to Hamed or to the Varan tree. rt1 cannot discharge it from here (rule 11, and the project boundary) |

### D39 — NEW ROW, opened 2026-08-09 (found incidentally by D38-COV)

| row | bucket | basis |
|---|---|---|
| **D39** — flexible-array-member union sized differently by clang and MSVC | **DISCLOSE (provisional)** | **MEASURED 2026-08-09.** `STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE` (`winioctl.h:13430`, Windows SDK 10.0.19041.0) at `thumbv7-unknown-windows-msvc`: **rt1 clang-cl gives alignof 4 / sizeof 12; MSVC 14.16 ARM gives alignof 4 / sizeof 76 — a 64-byte disagreement**, derived by wrapper member offsets on both compilers. Mechanism: an anonymous **union whose only members are flexible arrays** (`Lev1Depends[]`, `Lev2Depends[]`). clang sizes the flexible arrays as zero-length; MSVC reserves an element. **This is NOT D38a** — no virtual base is involved, and the mechanism is unrelated to virtual-base tail rounding. It was surfaced because `d38scan.py`'s invariant (`sizeof %% alignof != 0`) is deliberately broader than D38a: the inner union is `1/4`. **NOT LIVE in the corpus:** the pass-1 sweep never laid this record out, so nothing uses the type; only the `-complete` sweep, which forces every declared record, sees it. ⚠ **But the type is an IOCTL response struct**, so a 64-byte size disagreement would be real if any consumer ever passed it to `DeviceIoControl` — that is what makes this DISCLOSE rather than NOT-A-BUG. ✅ **FAMILY BOUNDED 2026-08-09** (`scratch/D39/FAMILY-BOUND.md`): across the corpus's ENTIRE include set there are **two** FAM-in-union candidates and **only one diverges**. `CLUSPROP_SECURITY_DESCRIPTOR` AGREES (28/28) because its union also holds a *non-flexible* member which sets the size. **So the trigger is specifically a union whose members are ALL flexible arrays** — a sharper condition than 'FAM in a union'. Mechanism, MEASURED (element sizes are identical on both compilers, so the elements are not the disagreement): MSVC 76 = 8-byte header + **one 68-byte `LEV2_ENTRY`**; clang 12 = 8 + 4, the all-FAM union sized as effectively empty. ✅ **Upstream searched** (2 phrasings recorded in the family-bound doc): **no direct hit**; closest is [#84565](https://github.com/llvm/llvm-project/issues/84565), CLOSED and about clang **accepting** the syntax, explicitly not about `sizeof`. **Per standing caveat 3 that is 'two searches failed', NOT 'unreported'** — D39 may not be written up as a new finding on this basis alone. ⚠ **Still owed:** whether any Varan consumer uses an all-FAM union type — a tree question, handed off as **H-D39**. Nothing found or nothing size-dependent → DISCLOSE ships as one release-note line; a size-dependent use → that consumer becomes the validation subject and this row reopens as a patch candidate |

### The 15 OPEN rows

**2026-08-10: five rows left this table this pass** — D11 and D13 moved to FIXED-BY-PATCH (V4/H-VA
and the 0008 rebuild respectively; see the master table); D26 and D27 moved to `ARMED —
DEMONSTRATION OWED` (their own closure criterion — "a floor that has never been shown to fire is
not armed" — is not met by a source comment asserting the demonstration; see the new sub-table
below); D34 moved to `CLOSED` (refuted by the filesystem — `ls stage/bin` = 9 `.exe`, all nine
carrying `7653a13d8…`). None of the five is deleted from the record: D11/D13/D26/D27 keep their
per-row evidence blocks below (updated in place), D34's is in the master table and in
`UPSTREAM-LEDGER.md`'s D34 row (grep `| D34 |`). ⚠ **Pre-existing, not touched this pass:** this table also carries D14
(master verdict `DISCLOSE, SETTLED`) and D38a/D38b (never part of the 38-row master table at all)
— all three were already here before 2026-08-10, tracked through the same D4 triage process even
though none is literally OPEN by verdict. The **master table's own OPEN count is 13**, not the 15
rows below; see the Tally for the reconciliation.

| row | bucket | the door, the oracle, or the reason |
|---|---|---|
| **D29** — `checkfix.sh` hardcodes a dead scratchpad | **FIX-NOW** | It is the *named Bug-5 acceptance instrument* and currently cannot be pointed at an rt1-built object, so Bug-5 acceptance cannot be re-run at all. **Oracle:** run it against a known-FIXED object (must report clean) **and** a known-unpatched object (must report the defect). **NOT DONE this session** |
| **D14** — `__declspec(align(K))` below natural alignment | **DISCLOSE** | Points at **[#63257](https://github.com/llvm/llvm-project/issues/63257)** (i686, `align(N)` N≤4, CLOSED/completed 2023-06-13). MSVC is **itself self-inconsistent** here (`C4359` then honours it), so "match MSVC" is not obviously the right target. rt1 states the divergence and does not change behaviour |
| **D38b** — self-inconsistent `sizeof`/`alignof`, 32-bit MS-ABI | **DISCLOSE** | On `i686` **clang matches MSVC exactly, including MSVC's own inconsistency** (both 8/20). Not a divergence. What is clang-specific is the array rejection, which is a *consequence* and disappears when D38a is fixed |
| **D25** — PDB-publics census blind spot | **DISCLOSE** | Bounded at ~4 % per PE across 17 PDB-only PEs. The bound is the deliverable; no fix is owed |
| **D38a** — ARM32 `sizeof` 20 vs MSVC 24 | **DISCLOSE** | **SETTLED 2026-08-09. `scratch/D38/E-VERDICT.md`. Real clang defect, but NO PATCH.** **Real:** MSVC 14.16 ARM gives 8/**24** where clang gives 8/**20** — third independent method (wrapper member offsets), agreeing with direct `sizeof` and array stride. **ARM32-only:** i686 and x86_64 AGREE with MSVC; **aarch64 was NOT measured against MSVC** (clang gives 8/24; no MSVC ARM64 arm was run), so unlike D14 this is not MS-ABI-wide. **Carrier count: ZERO across 2,582 TUs**, with the floor confirmed firing *through the sweep's own worker path* (the injected repro reports `V1`+`V2`) and a coverage denominator of 59/60 TUs producing dumps at ~431 records/TU — so the zero is an absence of carriers, not of compilation. **Structurally bounded:** an ARRAY of a carrier is a **loud compile error**, so the fleet cannot contain one; only non-array `sizeof` dependence was ever at risk, and with zero carriers that surface is empty. **A patch would be an INVENTION, not a port** — the over-aligned-base family ([#210461](https://github.com/llvm/llvm-project/issues/210461), `bd7bb26`) is a different mechanism, needs an `alignas` base D38's repro lacks, and is *"gated to Arm64 only"*. ⚠ **0010 is NOT opened; 0009 stays reserved for the D37 C-backport.** ✅ **LIMIT RETIRED 2026-08-09 by D38-COV.** rt1 carries 0008 — the fix for the very crash that blocked `-complete` — so the full sweep ran on rt1 and is impossible on stock. **Full declared-record coverage: 2,582/2,582 TUs, 7,018,478 records (2,718/TU vs pass-1's 431, 6.3×), zero non-zero exits, zero silent TUs, and ZERO D38a-class carriers.** The claim is now *no carrier exists among declared records in the corpus*, not merely among live ones. Varan-tree half handed off as **H-D38** |
| **D22** — LAYOUT-FUZZ corpus gap | **DEFER-DOOR** | **Blocker CLEARED this session:** `vbank.py`'s member parser is repaired and armed (`--self-test`, must-fail demonstrated). MEASURED: the repair recovers **148 probes over 400 shapes, +46.7 %** — the old sweep was probing ~68 % of the members it claimed. Door: resume 400 → 12,000 |
| **D15** — compiler-rt builtins | **DEFER-DOOR** | **Semantics half DECIDED this session** (`scratch/W3/D15-DIV0-DECISION.md`): divide-by-zero must trap, matching MSVC `__brkdiv0` (MEASURED in `libcmt.lib` `arm/divide.obj`). Gate `scratch/W3/div0_check.py` is armed both ways and **fails the prototype today**. Door for the remaining CMake half: the compiler-rt files named in `scratch/D2/…§1` |
| **D32** — ARM LTO through `lld-link` | **DEFER-DOOR** | ⚠ **rt1's `lld` carries the codegen fixes (0001/0003/0004) and nobody has run them under LTO.** Door + oracle: `scratch/F4/peicheck2.py` over an `lld-link` **LTO** link of a known Bug-1/Bug-2 carrier |
| **D35** — MinGW ARM32 blast radius | **DEFER-DOOR** | Scope is measured (Bugs 2 and 4 reproduce on `windows-gnu`); only rt1's validation is missing. Door: the banked Bug-2/Bug-4 repros re-run on `thumbv7-windows-gnu` |
| **D37** — `musttail`→sret hard error | **DEFER-DOOR — NOT IN THIS RELEASE** (⚠ **DEFER-DOOR is a disposition of an OPEN row, not a closure.** It records that the door was priced and left shut for this release — `scratch/D37/D37-DEFER-DOOR.md` — not that the defect went away. D37 stays in the OPEN count.) | **Door, stated precisely: backport BOTH `c1eb790cd2f2` and `82e64721974b`, for a future one-off only — this release does not carry it — gated on `scratch/D37/R3-C-GATE.md` GATE 1 (byte-identical Varan fleet rebuild) and GATE 2 (runtime acceptance).** The device trip completed 2026-08-09 (H4/H5/H6, all green) but that trip did not include this door — it is not scheduled against this release. ⚠ **The one-line backport was TRIED AND REVERTED.** Candidate 0009 (`82e6472` alone) was MEASURED **NO-IMPROVEMENT**: stock 18.1.8 fatal / rt1+0009 **same fatal** / clang 22.1.8 rc=0. Residual fatals are the **stack-argument shapes** — S (6×`i32`) and L (5×`i64`) — which is `c1eb790cd2f2`'s territory (**+9 / −100, net −91**; 109 was the diffstat churn bar, not a deletion count — *"the actual limitation is that the callee can't need more stack space for its arguments than the caller does"*). The patch is preserved at `patches/candidates/0009-arm-sret-tailcall.CANDIDATE.patch`, **out of the shipping series**. **Banked and reusable as the first half of C's acceptance:** armed floor fires, the mismatched-sret case is still refused, and mechanically **r0 is never written and SP net change is 0** across all four shapes. Upstream adjacents: [#104794](https://github.com/llvm/llvm-project/issues/104794), [#131124](https://github.com/llvm/llvm-project/issues/131124). **First fixed upstream: LLVM 20** (19.x still `\|\|` at `:3058`; 20.x `!=` at `:3175`) |
| **D31** — five auxiliary binaries not rebuilt (incl. `llvm-dwp`) | **DEFER-DOOR** | PKG-1. All five carry a full ARM backend (screen re-armed, 62/62 stock `.exe` — see D31 detail block), so they **can** reproduce the bugs rt1 fixes — that is why it is a door and not a DISCLOSE |
| **D06** — `VFPRegister` missing `sizeof` assert | **USER-ACTION** | Varan source, handoff **H3** |
| **D10** — Bug-5 Varan-side mitigations | **USER-ACTION** | Varan source. **H4 relink is DONE (rc=0, 2,585 objects / 21 PEs (19 ours)); H7 is now UNBLOCKED but is VARAN-SIDE and independent of the rt1 upstream work.** ⚠ **H7's own rule stands: REMOVE the libffi `optnone` lever and RE-VERIFY the frame layout — do not assume. The lever was layout luck, not trigger removal.** |
| **D28** — `split8.py` unsound | **USER-ACTION** | rt1 side already quarantined and replaced by `bug5_pred.py`. What is outstanding is the **Varan-side banner (H2)**, which only Hamed can install |
| **D36** — zero upstream filings | **USER-ACTION** | Rule 11. Not a question, a task. See W5's send-now / hold split |

### The 2 ARMED — DEMONSTRATION OWED rows

Neither OPEN nor CLOSED — per the decision above, a floor shown clean is worthless without an
armed both-directions transcript, and none is banked for either row yet.

| row | evidence present | evidence NOT present |
|---|---|---|
| **D26** — `gate-thunks.py --expect-min` floor | `--expect-min 178 --class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19 --max-review 844` present at both production call sites, `run-suite.sh` and `varan-fixup.sh` (byte-identical banked copies at `scratch/D26/banked-tooling/`, each at their gate-3/STANDING-GATES step), since **F0.2, 2026-08-04**; `gate-thunks.py`'s "`--expect-min` needs a separate value argument" hard-error check (banked at `scratch/D26/banked-tooling/gate-thunks.py`) turns the mistyped `--expect-min=178` spelling into a hard error | A run transcript showing the gate PASS at 178 and FAIL when raised above it. `gate-thunks.py`'s F0.2 (2026-08-04) arming comment, *"All four floors demonstrated firing"*, is a comment written by the change's own author, in the same file as the call — not a log, not dated against the code (the Varan tooling tree is not under version control) |
| **D27** — `gate-thunks.py` class/population coverage | The four-family census engine (`varan-thunk-override/census/engine.py`, recursive `os.walk`) armed at both call sites with `--class-floors B=44,4=73,R=0,adj=4217`, since **H1, 2026-08-09** | Same gap: no banked run record of each class floor firing in both directions, only the callers' own comment asserting it |

Handoff to the Varan side: run the floors at the census value (must PASS) and above it (must FAIL),
bank the transcript under `scratch/` and track it. Closes both rows on delivery.

### The 25 rows that are not open — listed so no row is omitted

**FIXED-BY-PATCH (8):** D01, D02 (0003) · D04 (0002) · D07 (0004) · D09 (0001) · D11 (0007) · D12 (0006) · D13 (0008).
*(Was 6. D11 moved this pass on H-VA's green hardware result; D13 moved this pass when 0008's
rebuild was reverified. This propagates the move the "(Was 6...)" note already flagged, into the
master table's own verdict cells and per-row evidence blocks — see D11/D13 there.)*
**NOT-A-BUG (12):** D03, D05, D08, D16, D17, D19, D20, D21, D23, D24, D30, D33.
**OS/PLATFORM-HAZARD (1):** D18.
**DISCLOSE (1):** D14 — pre-existing (its verdict cell already read `DISCLOSE, SETTLED` before
this pass), not part of the four-term vocabulary; recorded here for the first time so the count is
honest. Out of this pass's scope to reword.
**ARMED — DEMONSTRATION OWED (2):** D26, D27 — see the sub-table above.
**CLOSED (1):** D34 — see the master table row and `UPSTREAM-LEDGER.md`'s D34 row (grep `| D34 |`).

8 + 12 + 1 + 1 + 2 + 1 = 25. Each carries the measurement that settles it in the table below. Per
**working rule 12** — a confirmed defect gets both an rt1 patch and an upstream draft, as additive tracks, never alternatives — FIXED-BY-PATCH / NOT-A-BUG / OS-PLATFORM-HAZARD are the *only* verdicts that
discharge a defect without an rt1 patch; DISCLOSE (D14, pre-existing), ARMED and CLOSED are
process/disposition states, not verdicts drawn from the formal vocabulary.

### A tooling defect class, stated separately because it is not a compiler bug

**⚠ NEW ROW — D40, `gate-thunks.py` reads too few bytes (gate-vacuity #5, a new sub-class) ·
DEFER-DOOR.**
MEASURED 2026-08-10 during the release-notes verification: the `$B` thunk gate compares only
`data[off:off+2]` against the first halfword, but in `LDR.W <Rt>,[Rn]` the destination register
lives in the **second** halfword — so it **cannot distinguish `f8d0 c000` (r12, correct) from
`f8d0 1000` (r1, the Bug-1 defect)**, which is the one discrimination it exists to make.
**The 178/178 fleet result STANDS** — a verifier independently read all four bytes across all 178
and found one single form. The gate was right by luck about a clean fleet and would have been
equally silent on a broken one. Handed off as **H-GATE**: widen to four bytes, add a floor that
**FAILS** on a synthetic `f8d0 1000`, re-run. **Instrument repair, not a re-trip.**
This is a distinct sub-class from the earlier four: not an instrument that *cannot* fail, but one
that **reads too little to tell the two cases apart** — the byte-level form of working rule 15.

**Bucket: DEFER-DOOR** — door: **H-GATE**, widen the compare to four bytes and add a floor that
**FAILS** on a synthetic `f8d0 1000`; the 178/178 result stands on the independent four-byte read
already performed by the verifier, so this is an instrument repair, not a re-trip of the fleet.



**An A/B harness that cannot tell its own two arms apart.** Four instances, all in one week:
a "stock" negative control run with the **patched** compiler; `interesting_rt1.sh` pointed at the
patched compiler, where `llvm-reduce` reduces the module to nothing and reports **success**; a
dialect screen that could not fail on its target; and a must-fail control that exercised a
different code path than the one under test. Working rule 13 and `tools/ab_arm.sh` exist because
of these. **A fifth was avoided this session**: the first series-apply check ran `git apply --check`
against a *pristine* tree for each patch independently, which cannot detect patches that fail to
compose; it was re-run cumulatively (8/8 APPLIED; footprint at the shipped tree `7653a13d8` is **22 files, +1,239/−32** — the earlier '11 files, +253/−31' was the pre-0008 `bed948385` state) with a must-fail control.

---

## THE TABLE — 38 rows

| # | item | verdict | one-line basis |
|---|---|---|---|
| D01 | **Bug 1** — vPMF `$B` vcall thunk uses `r1` (AAPCS arg1 / hidden `sret`) as vtable scratch | **FIXED-BY-PATCH-0003** | oracle: `ldr r1,[r0]` → `ldr.w r12,[r0]` = `f8d0 c000` |
| D02 | **Bug 1 sub-class** — `$4`/`$R`/adjustor thunks, unprototyped, under **ordinary** mangled names | **FIXED-BY-PATCH-0003** | `musttail-varargs-forward-thisadjust.ll` PASSES on rt1, FAILS unpatched |
| D03 | **Bug 1 second emission site** — the tail-call **stack-argument shuffle** (`ldrd r1,r3,[sp] … strd r1,r3,[sp]`) | **NOT-A-BUG** | **RESOLVED 2026-08-05, mechanism named.** `ARMCallingConv.td:141`'s shadow list makes the register window a strict prefix, so a stack argument implies the window is exhausted — the unnamed variadic window is empty of registers whenever a shuffle exists. A/B: 52 stock/rt1 pairs → **48 identical, 4 differing, all 4 the vptr site (Bug 1 proper), none the shuffle** — 0003 changes nothing here. Fleet: **306 sites across the 19 PEs, ZERO carriers**. The one DEV instance is a **FALSE POSITIVE** of the census liveness model, reproduced byte-for-byte on **both** arms with a callee that ignores the argument (live-by-ABI ≠ value-needed). Catalog corrections owed Varan-side: **H-D03** |
| D04 | **Bug 2** — lld writes a local `__imp_` pointer to a Thumb function with bit0 clear | **FIXED-BY-PATCH-0002** | function slot `0x00401000`→`0x00401001`; data slot unchanged |
| D05 | **Bug 3** — MS bitfield straddling (mixed formal sizes get separate storage units) | **NOT-A-BUG** | clang-cl byte-identical to MSVC 14.16 ARM `cl.exe`; 12,000 shapes / 25,536 records, **0** divergences |
| D06 | **Bug 3's real in-tree victims' regression guard** — `VFPRegister` has no `sizeof` assert (`PoolHeader` does) | **OPEN** | the source fixes are real and landed; only one of the two is protected against silent regression |
| D07 | **Bug 4** — `-Zi` CodeView ICE `unknown codeview register D1_D2` (any tuple-register `DBG_VALUE`) | **FIXED-BY-PATCH-0004** | banked 5-line repro: unpatched = fatal, no object; rt1 = exit 0, 4,356-byte object |
| D08 | **Bug 4's "UNRESOLVED" `-Zi -Od` clean vs `-Zi -O0` ICE lane conflict** | **NOT-A-BUG** | clang-cl silently DROPS `-O0`; that lane was measuring `cc1 -Os`. `-Od` is clean. Neither lane was wrong |
| D09 | **Bug 5** — `emitPrologue` lowers SP 8 bytes too far under `splitFramePointerPush` | **FIXED-BY-PATCH-0001** | MIR histogram `{(r6,−8):33}` → `{(r6,0):33}`; prologue `sub sp,#0x154`→`#0x14c` |
| D10 | **Bug 5's Varan-side source mitigations** (AutoTArray substitution ×4, `nsDebugImpl::Break`, libffi `optnone`, VLA source-vigilance) | **OPEN — now actionable** | superseded by 0001 and **not yet removed**. **H4 is DONE, so H7 is UNBLOCKED.** ⚠ Removal is not the end of it: **re-verify the frame layout after removing the `optnone` lever** rather than checking only that the attribute is gone. The lever worked by layout luck, not by removing the trigger |
| D11 | **defect #6** (fixed by **patch 0007** — note the off-by-one) — ARM backend `report_fatal_error` on a `musttail` vararg forward that also calls `llvm.va_start` | **FIXED-BY-PATCH-0007** | **patch 0007 EXISTS**: commit `a20eeb750`, built, lit 9/9; V1/V2/V3 + 4 regression oracles all PASS with armed floors that were made to fire. **V4 (runtime `va_list`-contents exe) was the one open condition and is now MET**: H-VA returned GREEN on hardware 2026-08-09 — 11/11 cases exit 0, the must-fail companion failing case 7 and ONLY case 7 (exit 1). Oracle: `scratch/T8/ACCEPTANCE-0007.md` V1–V4. The pre-agreed ship rule is satisfied; 0007 SHIPS. See the D4 triage note on rows that left the table this pass ("2026-08-10: five rows left this table this pass", under "### The 15 OPEN rows") |
| D12 | **defect #7** (fixed by **patch 0006** — note the off-by-one) — `-Wpadded`/`-Wpadded-bitfield` never fire under `MicrosoftRecordLayoutBuilder` | **FIXED-BY-PATCH-0006** | stock 18.1.8 = 0 diagnostics → rt1+0006 = 7; corpus oracle 1355/1355 finding-for-finding vs clang 21 |
| D13 | **`-fdump-record-layouts-complete` crashes clang 18** (stock *and* rt1) | **FIXED-BY-PATCH-0008** | T9a named the crash site and the upstream fix (`e4882d83d77f`, first shipped LLVM 19, never backported to 18.x); 0008 is a verbatim port, commit `7653a13d8` (amended from `bed948385`). Oracle, armed: stock 18.1.8 segfaults 4/4 (both lit TUs × both triples); clang 21.1.8, which carries the same guard, passes and dumps exactly `Live<int>` + `Plain`, 0 `NoLayout` leaks. `build/bin/clang.exe` is rebuilt at `7653a13d8` and re-run — the STOP condition that held the rebuild is CLEARED. D13 no longer appears in the OPEN triage sub-table; it moved to FIXED-BY-PATCH-0008 on 2026-08-10 — see "### The 25 rows that are not open" and the Tally |
| D14 | **`__declspec(align(K))` below natural alignment inside a `#pragma pack(P)` region** — clang ≠ MSVC | ✅ **DISCLOSE, SETTLED** | 10 of 12,000 fuzz shapes; upstream clang behaviour (18.1.8 = 21.1.8 = rt1), and MSVC is itself self-inconsistent (C4359 then honours). **H-ALIGN ran to Stage 2 on the consumer tree: ZERO divergences**, so the construct does not occur and no patch is owed. Upstream family: [#63257](https://github.com/llvm/llvm-project/issues/63257) |
| D15 | **compiler-rt builtins gap** — no `clang_rt.builtins-*.lib` for a Windows thumb triple; `__aeabi_{u,}idivmod` unresolved | **CLOSED 2026-08-30: KEEP THE SHIM** | Both CMake gates MOVE, so they were never the blocker; the reason to decline is that compiler-rt's divide-by-zero **does not trap** where MSVC's `__rt_*` does. rt1.1 ships no builtins archive and **ships `aeabi-shim.c` instead** (`scratch/W3/D15-VERDICT.md`). ⚠ Row was **OPEN / "recon in flight as T9b"** until this batch, contradicting its own detail section below |
| D16 | **`__restrict` is part of the MSVC name mangling** — decl/def differing only in `__restrict` are two symbols | **NOT-A-BUG** | ABI conformance: MSVC encodes it (`PIBI` vs `PBI`), clang-cl matches for ABI compatibility |
| D17 | **MSVC signed unscoped enums** bite enum-bitfields and enum-shifts | **NOT-A-BUG** | WAI per the MS enum ABI; hits any MSVC-targeting build; **both** forms are diagnosable — bit-fields by `-Wsigned-enum-bitfield`/`-Wbitfield-constant-conversion`, shifts by **`-Wmicrosoft-enum-value`** (fires under `-Wpedantic`, exact coverage). Upstream thread #119228 |
| D18 | **A32 is device-lethal on Windows RT** — the kernel drops `CPSR.T` across preemption into A32 code | **OS/PLATFORM-HAZARD** | clang correctly emits `blx`; the death is OS behaviour. Consequence: Thumb-2 only, A32 JIT structurally impossible |
| D19 | **`alloca` 4×-undersize codegen bug** (`SetGenericFont`) | **NOT-A-BUG** | REFUTED as an undersize bug: `__chkstk` takes `r4` in **words**, `(27<<1)=54` words = 216 B = exactly `27×sizeof(nsCSSValue)` |
| D20 | **`js::jit::Operand` lays out 12 bytes under MS vs 8 under Itanium** | **NOT-A-BUG** | MS ABI WAI (`Tag : uint8_t` beside `uint32_t reg_:5`); counterfactual `Tag : uint32_t` measured 8/8. No consumer. Recorded, not fixed |
| D21 | **The other 30 MS-layout bitfield padding sites** in the Varan tree (incl. `SSLCipherSuiteInfoStr`, `js::wasm::CodeRange`) | **NOT-A-BUG** | 2,582 TUs / 31 sites / **0 real traps**; no `sizeof` assertion exists on any of the 31 |
| D22 | **LAYOUT-FUZZ corpus gap** — no inheritance, no virtual functions, no vtables | **OPEN** | the MS ABI is most distinctive exactly there; the Bug-3 closure does not cover it |
| D23 | **clang-cl driver argument spellings** — `-O0` silently dropped, `-g0` rejected as unknown | **NOT-A-BUG** | documented driver behaviour; production `/O1` is `cc1 -Os`. It cost two lanes, so it is recorded, not omitted |
| D24 | **`d3dcompiler_47.dll` is blind to the thunk census** (no PDB, no map; 1 unadjudicable shape-B hit) | **NOT-A-BUG** | prebuilt MS redist built by **MSVC in 2017** — a clang allocator defect cannot be present by construction |
| D25 | **PDB-publics blind spot** — internal-linkage anonymous-namespace adjustor thunks are not publics | **OPEN** | bounded at ~4 % per PE across the **17 PDB-only PEs**; unbounded only in the sense that it was never enumerated there |
| D26 | **`gate-thunks.py --expect-min` floor was never armed** (gate-vacuity instance **#11**) | **ARMED — DEMONSTRATION OWED (H-D26b)** | MEASURED: `--expect-min 178 --class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19 --max-review 844` is present at both production call sites, `varan-interwork/run-suite.sh` and `varan-thunk-override/varan-fixup.sh` (byte-identical banked copies at `scratch/D26/banked-tooling/run-suite.sh` / `varan-fixup.sh`, each at their "GATE 3/5"/"STANDING GATES" step), since **F0.2, 2026-08-04**. NOT measured: a run transcript demonstrating both directions (passes at 178, fails when raised above it) — a source comment asserting the demonstration is not the demonstration. See the D26 detail block and the D26 row in the D4 triage table (above, in "## D4 — THE TRIAGE") |
| D27 | **`gate-thunks.py` covered one mangling in two binaries** — `$4`/`$R`/adjustor classes were invisible | **ARMED — DEMONSTRATION OWED (H-D26b)** | MEASURED: a vendored class-census engine (`varan-thunk-override/census/engine.py`) covering all four thunk families via a recursive population walk is present at both call sites with `--class-floors B=44,4=73,R=0,adj=4217` since **H1, 2026-08-09**. NOT measured: a run transcript demonstrating each class floor firing in both directions. See the D27 detail block and the D27 row in the D4 triage table (above, in "## D4 — THE TRIAGE") |
| D28 | **`split8.py` is an unsound Bug-5 oracle** — false positives on FIXED output **and** a measured false negative | **OPEN** | QUARANTINED rt1-side and replaced; the Varan-side banner (H2) is not installed |
| D29 | **`checkfix.sh` cannot be redirected** — hardcodes `SP` to a dead session scratchpad | **OPEN** | it is the named Bug-5 acceptance instrument and cannot currently point at an rt1-built object |
| D30 | **rt1 builds only the ARM and X86 backends** — `clang -print-targets` 6 vs stock 42 | **NOT-A-BUG** | deliberate build configuration, measured and documented; AArch64 fails to select a target under rt1 |
| D31 | **Five auxiliary binaries are not rebuilt** — `clang-check`, `clang-repl`, `clang-scan-deps`, `clang-linker-wrapper`, `llvm-dwp` | **OPEN** | all five carry a full ARM backend (screen re-armed over the full 62-binary denominator), so they **can** reproduce the bugs rt1 fixes |
| D32 | **The ARM LTO path through `lld-link` is untested** | **OPEN** | rt1's `lld` does carry 0001/0003/0004, but no oracle ever ran through the LTO code generator |
| D33 | **The product target list cannot run lit** | **NOT-A-BUG** | measured build fact, documented with the exact 7 extra targets (+81 edges on this tree; the project record says +82) |
| D34 | **`stage/bin/` completed to 9 of the 9 driver copies** the overlay needs (2026-08-10) | **CLOSED** | REFUTED as still-missing: MEASURED, `ls stage/bin` = 9 `.exe` (`ld.lld.exe`, `ld64.lld.exe`, `wasm-ld.exe` now present, mtime 2026-08-10 03:34); all nine carry `7653a13d8d28189c7cef1401b934ec30d98ea353` (`grep -ac` = 2 on each). The project's working log's "9/9 driver copies" bullet (PKG-1 prep) records "9/9 driver copies staged". Closed by rt1's own packaging (PKG-1, WORKLIST T7) |
| D35 | **MinGW ARM32 (`thumbv7-windows-gnu`) is in the blast radius of 0001 and 0003 but is untested** | **OPEN** | `ARMCOFFMCAsmInfoGNU` also sets `ExceptionsType = WinEH`, so it takes the same `usesWindowsCFI()` path |
| D36 | **No upstream filing has been made** (rule 12's second track) — 6 drafts exist, 0 filed | **OPEN** | filing is the USER's action (rule 11); the drafts are complete for Bugs 1/2/4/5 and #6 |
| D37 | **`musttail` to a struct-returning function is a HARD ERROR on ARM32** — `sibcall` refused unconditionally when either side uses struct-return semantics | **OPEN** | NEW 2026-08-05, found while building 0007's V4 runtime check. `ARMISelLowering.cpp:3051-3052` @ `a20eeb750`: `if (isCalleeStructRet || isCallerStructRet) return false;` — **UNCONDITIONAL, no musttail exemption, PRE-DATES 0007 and untouched by it** (`git show --stat a20eeb750`). MEASURED **stock == rt1**: `sret`+**non**-variadic+no `va_start` fatals on both, so it is not about varargs at all. **Same family as defect #6, one guard over.** **UNPATCHED.** It made V4's required sret case **impossible by construction**, not merely untested — see A1 for whether the Bug-1 sret escalation survives it. Disposition: ~~candidate patch 0010~~ — **SUPERSEDED, patch number was wrong:** the candidate was authored as **0009** (`patches/candidates/0009-arm-sret-tailcall.CANDIDATE.patch`), tried and **REVERTED**; D38a's row already records *"0010 is NOT opened; 0009 stays reserved for the D37 C-backport"*. RECON REQUIRED — not auto-fix. #6's guard was conservative-with-precondition-already-satisfied; **D37's may be protecting something genuinely unimplemented**, which is a different cost class. **Schedule AFTER the Varan round-trip; it blocks nothing.** ⚠ **This row's verdict cell still reads OPEN and is CONTRADICTED by the D4-triage row above, which reads `DEFER-DOOR — NOT IN THIS RELEASE`.** The settled disposition and its itemised price are in **`scratch/D37/D37-DEFER-DOOR.md`** (RT1-UPSTREAM-2 item C, 2026-08-31). The verdict word is deliberately **left unchanged pending the user's decision**, because flipping it moves the master OPEN count from **13 to 12** — a shipping number carried at **FIVE** sites in this table *and* in the frozen `stage/` copy: line 104 (prose), **242** (the Tally row `| OPEN | **13** |` — the load-bearing one), 255 (the open list, which names D37 explicitly), 256 (`8+12+1+1+2+1+13 = 38`, which would also stop summing to 38) and the `**13 OPEN rows**` sentence — **draft line 784, frozen line 764**, the one site whose line number differs between the two copies. An earlier note here said "lines 104 and 255", which undercounted by three; a count is not a thing to move as a side effect of a cross-reference, least of all one whose own sites were miscounted. |
| D38 | **clang emits `sizeof` 20 with `alignof` 8 for a record with a VIRTUAL BASE** — a size that is not a multiple of its own alignment, and clang then **REJECTS any array of the type** | **OPEN** | NEW 2026-08-05 (D3, seed `20260805`). `struct I4 { int q; }; struct V1 : virtual I4 { double d; };` → clang 8/**20**, MSVC 14.16 ARM 8/**24**. Dump-free oracle (`ShowSize<N>`), no layout dump involved. **NOT an rt1 regression** — rt1, stock 18.1.8 and clang 21.1.8 emit an identical value vector. **24 of 400 pilot shapes carry a divergence** (20 with a virtual base, 4 without); 192 rows, 2 signatures. **STOP honoured at pilot size — the full 12,000-shape sweep has NOT run and NO triage was done.** Repros: `scratch/D3/repro_vbase_tailpad{,_array}.cpp`. Row **D22 stays OPEN** — the coverage gap was probed, not closed. ⚠ Fix `vbank.py`'s member-parsing regex first (the "MEMBER PARSING" block in `scratch/D3/vbank.py`; note this was subsequently repaired — see D22): it silently drops array and align-attributed members, under-reporting probe coverage without warning |

### Tally

| verdict | count |
|---|---|
| FIXED-BY-PATCH-N | **8** |
| NOT-A-BUG | **12** |
| OS/PLATFORM-HAZARD | **1** |
| DISCLOSE (pre-existing outlier — see note) | **1** |
| ARMED — DEMONSTRATION OWED | **2** |
| CLOSED | **1** |
| OPEN | **13** |
| **TOTAL** | **38** |

Derivation (2026-08-10, re-derived from the master table's own verdict cells, row by row, via
`grep` — not hand-counted): FIXED-BY-PATCH-N = D01,D02,D04,D07,D09,D11,D12,D13 (8; D11 and D13
moved this pass — H-VA's green hardware result for D11, patch 0008's rebuild-and-reverify for
D13). NOT-A-BUG = D03,D05,D08,D16,D17,D19,D20,D21,D23,D24,D30,D33 (12, unchanged).
OS/PLATFORM-HAZARD = D18 (1, unchanged). **DISCLOSE = D14 (1) — found during this pass's
re-derivation, NOT introduced by it: `✅ **DISCLOSE, SETTLED**` was already D14's verdict cell
before any edit this pass, a fifth value outside the four-term vocabulary that predates 2026-08-10.
Recorded here so the arithmetic is honest; fixing D14's verdict wording is out of this pass's
scope.** ARMED — DEMONSTRATION OWED = D26,D27 (2, moved this pass from OPEN — see the D26/D27
rows). CLOSED = D34 (1, moved this pass from OPEN — refuted by `ls stage/bin`). OPEN = the
remaining 13: D06,D10,D15,D22,D25,D28,D29,D31,D32,D35,D36,D37,D38 (D14 excluded — it is DISCLOSE,
not OPEN, and always was). 8+12+1+1+2+1+13 = 38.

Patch coverage of the FIXED rows: **0001** D09 · **0002** D04 · **0003** D01, D02 · **0004** D07 ·
**0006** D12 · **0007** D11 · **0008** D13. Patch **0005** is test-only (lit coverage for D02) and
therefore closes no row of its own.

---

## PER-ROW EVIDENCE

### D01 — Bug 1, `$B` vcall thunk · FIXED-BY-PATCH-0003

- Patch on disk: `D:\repo\llvm-rt\patches\0003-arm-forwarded-musttail-regs.patch`, 11,685 bytes `[measured]`.
- Commits in the rt1 tree: `a1f390894 [ARM] Model the forwarded argument registers of a musttail vararg forwarder` and `3afb49879 [ARM] Fix two defects in the musttail forwarded-register patch found by review` `[measured]`.
- Oracle (A/B vs unpatched 18.1.8), `RT-CLANG-FIX-1.md` §1:
  `unpatched: ldr r1,[r0] ; ldr r1,[r1,#0x4] ; bx r1` → `rt1: ldr.w r12,[r0] ; ldr.w r12,[r12,#0x4] ; bx r12`, byte-exact `f8d0 c000`.
  The must-fail control is the unpatched column and it fires.
- Root cause (catalog `:124-169`, `RT-CLANG-RECON-1.md` §3): a missing forwarded-register liveness model, **not** a hardcoded register. The AArch64 mirror is `AArch64ISelLowering.cpp:6966-6974`.
- Blunt fix (pin `TCRETURNri` to `r12`) is REFUTED three independent ways — do not re-propose it.
- Upstream: **UNFIXED on `main`**. Draft ready at an upstream filing prepared but **NOT YET FILED** (31,580 bytes) `[measured]`. → see D36.
- Consequence for Varan: the `varan-thunk-override` COMDAT override becomes unnecessary — but only after H4 proves it (that is D10's scope, not this row's).

### D02 — Bug 1 sub-class, `$4`/`$R`/adjustor · FIXED-BY-PATCH-0003

- `RT-CLANG-FIX-1.md` §5: P8 was resolved with **no fifth patch**. Measured in IR, the `$4` thunk is emitted as a *variadic* function containing a `musttail` call, so `hasMustTailInVarArgFunc` fires and the scratch moves r1→r12. `$R` covered too (two temps landing in `{r12, r0}`).
- Prediction converted to measurement: `musttail-varargs-forward-thisadjust.ll` **PASSES on rt1 and fails on the unpatched compiler** (`RT-CLANG-FIX-1.md` §2, 5/5 lit; the project's working log, 6/6 lit).
- The carrier class is real and was **built**: `scratch/F05V/vctrlB.dll` 0x10001064 `?k@WD@@$4PPPPPPPM@A@AAHP8MP@@AAHXZHHH@Z` emits `ldr r1,[r0,#-4]` under an ordinary mangled name; its prototyped twin at 0x10001082 emits `ldr r12,[r0,#-4]` from the same run.
- Fleet position: FLEET-CENSUS — RELEASE build 4,334 thunks / 19 our-built ARMNT PEs / **0 carriers**.

### D03 — Bug 1's second emission site (tail-call stack-arg copy) · ~~OPEN~~ **NOT-A-BUG (mechanism named)**

> **CLOSED 2026-08-05 by the D03 ADVERSARIAL VERIFIER (working rule 9).** Everything below is the
> state of the row *before* it was measured, kept for the audit trail. What changed, all `[M-D03V]`
> and all re-run independently of the measuring agent with `ab_arm_two` identity armed
> (`clang version 18.1.8` vs `Varan clang version 18.1.8-rt1 (…a20eeb750…)`):
>
> 1. **"no A/B oracle was ever run on this shape" is now FALSE.** 13 measurable IR shapes × 4 opt
>    levels × 2 arms recompiled from scratch: comparing **raw `.text` bytes**, 48 identical / 4
>    differing, and all 4 are `s11_bug1_positive` (the vptr site). 4 further shapes (`s04`, `s05`,
>    `s10`, `s12`) are **backend-refused identically on both arms** at all 4 levels — `sret` and
>    `byval` veto musttail on ARM (`ARMISelLowering.cpp` stock `:3037-3038` / `:2971-2977`), so the
>    **`sret` axis is not measurable on ARM32 and carries zero weight in either direction.**
> 2. **"WHAT WOULD CLOSE IT" is satisfied, including its must-fail control.** The stated control was
>    *"the stock column still emitting `ldrd r1,r3,[sp]`"* — it **fires** once the callee is defined
>    in the same TU: `scratch/D03/verify/devcarrier_v.cpp` MODE=2 at `clang-cl -O1 -Oi` emits
>    `e9dd 1300 ldrd r1,r3,[sp] / 38d8 subs r0,#0xd8 / e9cd 1300 strd r1,r3,[sp] / b.w`, byte-for-byte
>    the `DEV xul.dll` 0x10ec0e00 carrier (bytes re-read from the shipped binary this session:
>    `dd e9 00 13 d8 38 cd e9 00 13 ff f7 d2 bf`). MODE=3, one variable — the callee also reads
>    `aDocument` — emits `ldrd r3,r12` instead. **Stock and rt1 are identical in every mode**, so
>    "if rt1 still emits argument registers there, patch 0003 is incomplete" does **not** follow:
>    the registers are *correctly* dead.
> 3. **The mechanism, and why this is not a second live site.** `r1` in the carrier is live by
>    AAPCS and **dead in the callee** (`aDocument` is referenced only by `NS_PRECONDITION`); clang
>    modelled it and proved it. Bug 1 is the *unnamed variadic forwarded window*, and that window
>    and a stack shuffle **cannot coexist**: MEASURED over 781 variadic musttail **vcall**
>    forwarders (`verify/coexist2.py`, where the indirect call forces a scratch pick so a non-empty
>    window is directly observable as an A/B difference) — **670 have a shuffle, 13 have a non-empty
>    window, 0 have both**; 13 is exactly the AAPCS-predicted count. Plus 3,906 direct-call shapes
>    (`verify/coexist.py`), same null result.
> 4. **Fleet, re-run:** 306 sites in the 19 our-built ARMNT REL PEs, 18 whose scratch touches r0–r3,
>    **0 carriers**; all 18 re-disassembled by hand from the shipped bytes and every verdict upheld.
>    `gate-thunks.py` is blind to **306/306** (measured: 0 anchors match its `??_9…$B…` regex,
>    the `THUNK_RE` pattern near the top of `gate-thunks.py`, banked byte-identical at
>    `scratch/D26/banked-tooling/gate-thunks.py`); the census had jurisdiction over **12/306**
>    (`scratch/CENSUS/census3.py`'s `thunks = {va: ns for va, ns in byva.items() ...}` filter line
>    keeps only dbghelp `[thunk]:` symbols).
>
> **Owed elsewhere (NOT applied from here):** the Varan catalog, `CLANG-CL-THUMBV7-BUGS.md:193-194`
> in its own tree, states as INFERRED *"the allocator would not
> have taken r1/r3 as scratch had it modelled r0-r3 as forwarded"* — **REFUTED**. It is a
> HANDOFF-TO-VARAN item; the catalog is read-only from here.

- The shape, catalog `:190-194`: `ldrd r1,r3,[sp] ; subs r0,#0xd8 ; strd r1,r3,[sp] ; b.w <target>` — both `imm8 = 0`, i.e. two stack words copied onto themselves, costing two live argument registers. The one real fleet carrier (`DEV xul.dll` 0x10ec0e00 `PresShell::ContentStateChanged'adjustor{216}'`) clobbers **through this site, not through `ldr r1,[r0]`**.
- **WHY OPEN:** the catalog labels the claim that patch-0003's mechanism also fixes this site **INFERRED** (catalog `:193-194`: *"INFERRED (predicted by, and consistent with, the root cause above)"*). Every rt1 oracle for D01/D02 measured the **vptr-load** site. No A/B was run on the stack-argument-copy shape — `RT-CLANG-FIX-1.md` §1's Bug 1 row and §5 are both vptr-load evidence.
- **WHAT WOULD CLOSE IT:** recompile the DEV-objdir TU that produces `PresShell::ContentStateChanged'adjustor{216}'` (or a synthetic forwarder with ≥2 stack arguments and an unprototyped signature) with stock 18.1.8 and with rt1, and disassemble. Must-fail control = the stock column still emitting `ldrd r1,r3,[sp]`. If rt1 still emits argument registers there, patch 0003 is incomplete and a lit test for the shape is owed.

### D04 — Bug 2, lld local `__imp_` Thumb bit · FIXED-BY-PATCH-0002

- Patch: `patches/0002-lld-coff-localimport-thumb-bit.patch`, 4,607 bytes; commit `e24a313bc` `[measured]`.
- `[read-in-source]` the landed code, `Chunks.cpp:867-880` (lld's COFF linker, in this project's `llvm-project` checkout) at `345ce564e`:
  ```cpp
  void LocalImportChunk::writeTo(uint8_t *buf) const {
    if (ctx.config.is64()) {
      write64le(buf, sym->getRVA() + ctx.config.imageBase);
    } else {
      uint32_t bit = 0;
      // Pointer to thumb code must have the LSB set, so adjust it. Only code is
      // adjusted: dllimport of a locally defined variable is valid, and the
      // pointer to such a variable must stay unmodified.
      if (ctx.config.machine == ARMNT && sym->getChunk() &&
          (sym->getChunk()->getOutputCharacteristics() & IMAGE_SCN_MEM_EXECUTE))
        bit = 1;
      write32le(buf, (sym->getRVA() + ctx.config.imageBase) | bit);
    }
  }
  ```
- Oracle, `RT-CLANG-FIX-1.md` §1: one link containing both a `dllimport` function and a `dllimport` variable — function slot `0x00401000` → `0x00401001` (odd, fixed); **variable slot `0x00403000` unchanged in both**. The unchanged data slot is the absent-control: an unconditional ARMNT OR would have corrupted it.
- The standing Varan gate with the post-link fixer never run: `OLD: GATE FAIL … slot RVA 0x2004 -> 0x00401000` → `RT: GATE PASS`.
- Upstream: **UNFIXED on `main`** (`LocalImportChunk::writeTo` byte-identical 18.1.8 / 21.x / main). Draft an upstream filing prepared but **NOT YET FILED**. Precedent lines corrected for this tree: `lld/COFF/DLL.cpp:543/:614/:615`. → D36.

### D05 — Bug 3, MS bitfield straddling · NOT-A-BUG (for the compiler)

**The measurement that settles it (two independent ones):**

1. Hand-shape A/B vs the project's own reference compiler — MSVC 14.16.27023's ARM `cl.exe`, reporting itself as **cl 19.16.27054 for ARM** — using `/d1reportSingleClassLayout` on both sides so the comparison is field-for-field. Dumps **byte-identical**:

   | shape | MSVC ARM | clang-cl thumbv7 | Itanium (armv7-linux) |
   |---|---|---|---|
   | `{u32:15, bool:1, u32:16}` (`PoolHeader` pre-fix) | **12** | **12** | 4 |
   | `{u32:15, u32:1, u32:16}` (post-fix) | 4 | 4 | 4 |
   | `{enum:2, u32:5, bool:1, bool:1}` (`VFPRegister` pre-fix) | **8** | **8** | 4 |
   | `{u16:5, u32:5}` — no `bool` anywhere | **8** | **8** | 4 |

2. **LAYOUT-FUZZ at scale** (the project's working log): **12,000 generated shapes · 25,536 records compared · 0 compile failures · 0 parse failures · 0 skipped · ZERO divergences on the bitfield axis**, including 3,149 shapes composed exclusively of mixed-underlying-size bitfield runs. Armed floor: pointing the clang side at Itanium makes the same generator and driver report **2,058 divergences** over the same records — so the sweep is provably non-vacuous.

- Governing rule `[read-in-source]`, `RecordLayoutBuilder.cpp:3040-3044` (clang's AST library, in this project's `llvm-project` checkout) at `345ce564e` (line drifted from `:3028` pre-0006):
  ```
  // Check to see if this bitfield fits into an existing allocation.  Note:
  // MSVC refuses to pack bitfields of formal types with different sizes
  // into the same allocation.
  if (!UseExternalLayout && !IsUnion && LastFieldIsNonZeroWidthBitfield &&
      CurrentBitfieldSize == Info.Size && Width <= RemainingBitsInField) {
  ```
  A pure **size** comparison — not signedness, not `bool`, not type identity.
**SCOPE — the rule is MS-ABI-wide, not an ARM32 defect and not UXP-specific `[measured]`.**

Probe `t10probe.cpp` (this project's working tree, outside the shipped `scratch/`), **stock unpatched clang 18.1.8**, `-fsyntax-only`,
sizes read out of an incomplete-template-argument error (`S<N>`) so **no layout dump is involved**:

```cpp
struct MixedBoolU32 { bool b : 5;           unsigned u : 5; };  // differing declared types
struct MixedU16U32  { unsigned short a : 5; unsigned u : 5; };  // differing, no bool at all
struct SameU32      { unsigned a : 5;       unsigned u : 5; };  // uniform declared type
struct SameU16      { unsigned short a : 5; unsigned short u : 5; };
```

| target | MixedBoolU32 | MixedU16U32 | SameU32 | SameU16 |
|---|---|---|---|---|
| `i686-pc-windows-msvc` | **8** | **8** | 4 | 2 |
| `x86_64-pc-windows-msvc` | **8** | **8** | 4 | 2 |
| `aarch64-pc-windows-msvc` | **8** | **8** | 4 | 2 |
| `thumbv7-unknown-windows-msvc` | **8** | **8** | 4 | 2 |
| `x86_64-unknown-linux-gnu` | 4 | 4 | 4 | 2 |
| `aarch64-unknown-linux-gnu` | 4 | 4 | 4 | 2 |

Four consequences, each carried by a column of that table:

1. **MS-ABI-wide.** The four MS rows are identical digit for digit — `thumbv7` is in no way special,
   `i686` behaves the same. Calling this an ARM32 bug is the same category error as calling it a
   clang bug.
2. **The trigger is DIFFERING DECLARED TYPES; `bool` is incidental.** `{u16:5, u32:5}` diverges
   8-vs-4 exactly as `{bool:5, u32:5}` does. This is the same widening the catalog already applied
   to its audit item, now measured on four MS targets instead of argued from the source rule.
3. **The source fix is PORTABLE — the load-bearing point.** `SameU32` is 4 and `SameU16` is 2 under
   **both** ABIs, so making the declared types uniform yields *identical* layout on MS and Itanium.
   It is a genuine portable fix, not a Windows-only workaround.
4. **The instrument is armed (must-fail control):** the two Itanium rows differ from the four MS rows
   in the same run, so "no difference anywhere" was an outcome this probe could have reported and
   did not.

**Why UXP met it only on this port (INFERRED, from where the instances live):** both victims are in
`js/src/jit/arm/` — ARM32-only source that had never been compiled under the MS ABI, since Firefox
on Windows-ARM is ARM64 and uses `jit/arm64`. A universal rule meeting historically unexercised
source. This is the single most likely trap for a community porter bringing Linux-developed code to
RT, which is why it belongs in the release README despite being NOT-A-BUG.

**Fix vs detector, stated separately so they are not confused:**

- **FIX = source** — uniform declared type (or explicit masks). Portable, per column 3 above.
- **NOT-A-FIX = any compiler-side layout change.** It would desync rt1's output from every
  MSVC-built ARM library including the 14.16 CRT that Varan links against. This is why the row is
  NOT-A-BUG rather than OPEN: there is no compiler change that would be an improvement.
- **DETECTORS** = a per-struct `static_assert(sizeof(...))` (D06) plus `-Wpadded`, the latter usable
  under MS layout **only because of patch 0006** (D12).
- README framing that follows from those three: **rt1 cannot prevent this class; it makes it
  VISIBLE.**

- **The wrong attribution, named:** the catalog's slot 3 is a tombstone precisely because the compiler was blamed for a source defect. **No codegen patch is owed and none exists.** Not to be filed upstream.

**BUT the source-side defect was real, and it had real in-tree victims — both facts belong in this row:**

- `js::jit::VFPRegister` (`uxp/js/src/jit/arm/…`) — the `bool` members, not the "small enum": measured 8 (MS) vs 4 (Itanium). Fixed at source by giving the members the same formal size (`uint32_t`).
- `PoolHeader::Header` — same family; fixed at source; **caught at compile time** by upstream's own `JS_STATIC_ASSERT(sizeof(Header) == sizeof(uint32_t))` at `uxp/js/src/jit/arm/Assembler-arm.cpp:5256` and `:5262`.
- Batch-4's `Assembler-arm.h` — third instance.
- The source fixes stay exactly as they were. Only the *attribution* changed, and with it the audit scope: **any struct with two or more adjacent bitfields whose declared types differ in size**, `bool` or not.
- The regression guard for those source fixes is D06.

### D06 — `VFPRegister` has no `sizeof` assert · **OPEN**

- **WHY OPEN:** measured asymmetry — `PoolHeader` **is** asserted (`Assembler-arm.cpp:5256`/`:5262`); scanning `js/src/jit` for `sizeof(VFPRegister)` / `sizeof(FloatRegister)` returns **zero hits**, while the same scan shape finds the `PoolHeader` assertions immediately. That asymmetry is exactly why one victim was silent and the other was not.
- Owner: **Varan side**, `HANDOFF-TO-VARAN.md` **H3**. Not actionable from this project's working tree (rule: boundary).
- **WHAT WOULD CLOSE IT:** H3 lands — `static_assert(sizeof(js::jit::VFPRegister) == 4, …)` plus the sweep for other fixed-at-source structs lacking one — with H3's own acceptance met (a deliberately wrong assert value must fail the build, proving the asserts are live). `js::jit::Operand` stays untouched by explicit decision (see D20).

### D07 — Bug 4, CodeView tuple-register ICE · FIXED-BY-PATCH-0004

- Patch: `patches/0004-mc-codeview-fallible-regnum.patch`, 13,079 bytes; commit `17fd79072` `[measured]`.
- `[read-in-source]` the landed API, in this project's `llvm-project` checkout at `345ce564e`:
  `llvm/include/llvm/MC/MCRegisterInfo.h:444` `int getCodeViewRegNum(MCRegister RegNum) const;` and `:458` `std::optional<int> getCodeViewRegNumOrNone(MCRegister RegNum) const;`; `llvm/lib/MC/MCRegisterInfo.cpp:125` defines the fallible variant, `:138-139` re-implements the infallible one on top of it.
- Oracle, `RT-CLANG-FIX-1.md` §1: banked 5-line NEON repro at `-Zi -O1` — `unpatched: fatal error: error in backend: unknown codeview register D1_D2` (no object) → `rt1: exit 0, no ICE, 4,356-byte object`.
- lit: `DebugInfo/COFF/ARMNT/codeview-d-pair-register.mir` PASS.
- Two catalog attributions corrected and carried: the fatal is in the **MC layer** (18.1.8 `MCRegisterInfo.cpp:129` via `CodeViewDebug.cpp:1407`; `main` `:206` via `:1408`), and *"LLVM forgot to add table rows"* is wrong — **CodeView has no D-pair register**, so a graceful skip is the only truthful output. The trigger is **any tuple-register `DBG_VALUE`**, not NEON specifically.
- Upstream: **UNFIXED on `main`**. Draft is a **comment on the existing issue #64278**: an upstream filing prepared but **NOT YET FILED** (28,990 bytes) `[measured]`. → D36.

### D08 — Bug 4's `-Od` vs `-O0` lane conflict · NOT-A-BUG

- Catalog `:343-347` records it as **UNRESOLVED** ("one lane measured `-Zi -Od` clean … the other measured `-Zi -O0` ICEing on the same file").
- Settled in `RT-CLANG-FIX-1.md` §6: **clang-cl silently drops `-O0`** (only `/O[12xd]` are recognised), so that lane was measuring `cc1 -Os`. `-Od` is the only spelling that disables optimisation, and it is clean. **Neither lane was wrong.**
- Consequence carried into every opt-level claim: production `/O1` is `cc1 -Os`. See D23.

### D09 — Bug 5, prologue over-allocation · FIXED-BY-PATCH-0001

- Patch: `patches/0001-arm-frame-lowering-splitpush.patch`, 9,888 bytes; commit `07030b2b1` `[measured]`.
- `[read-in-source]` the landed fix, `ARMFrameLowering.cpp:963-972` (ARM backend, in this project's `llvm-project` checkout) at `345ce564e`:
  ```cpp
  } else if (STI.splitFramePointerPush(MF)) {
    // With a split frame pointer push, spill area 2 (the {r11,lr} pair) is
    // pushed *after* the DPR area … Using DPRCSOffset would lower SP by
    // GPRCS2Size too much …
    NumBytes = GPRCS2Offset;
  } else {
  ```
- Oracle 1 (`RT-CLANG-FIX-1.md` §1), pre-fix `nsRuleNode.cpp` unified TU, production flags, post-PEI MIR, per-frame-index error:
  `unpatched {('r6',-8): 33, ('r11',0): 2}` → `rt1 {('r6',0): 33, ('r11',0): 2}`. The two FP-resolved references were and remain exact — a built-in control inside the histogram.
- Oracle 2 (the project's working log), the sound MIR predicate `scratch/T3/bug5_pred.py` with **five armed controls, one variable each**; whole-module rt1-vs-stock over the 29 MB `.ll`: the two MIR dumps differ in **exactly 8 lines / 4 instructions**, every one a `tSUBspi` prologue allocation smaller by exactly 2 words:
  `WalkRuleTree 51→49 · SetGenericFont 85→83 · HasAuthorSpecifiedRules 91→89 · ComputePropertiesOverridingAnimation 65→63`. **Carrier count 5 → 0.**
- lit: `wineh-framepointer.ll` PASS with corrected immediates **1254/1256/1257** — upstream's own test had the bug baked into its expected output.
- IR reduction DONE: 29,272,948 B → **1,492 B / 43 lines** (19,620×), verified in both directions, attached to the upstream draft.
- **Upstream status (the one defect fixed upstream — and only on `main`):** `release/18.x` BUGGY · `19.x` BUGGY · `20.x` STILL BUGGY · `21.x` STILL BUGGY · `main` **FIXED** by `6c34ed7b3` "[ARM] Add support for Windows SEH (#184953)", 2026-05-18 — a **feature** PR with no bug label and no issue reference, i.e. fixed incidentally and never backported. **No shipping clang has it fixed.** Draft = a backport request, an upstream filing prepared but **NOT YET FILED**. → D36.

### D10 — Bug 5's Varan-side source mitigations · **OPEN**

- **WHY OPEN:** they are still in the Varan tree and 0001 has not yet been proven on it. Two of them carry different maintenance obligations and one is explicitly *not* root-cause removal:
  - `AutoCSSValueArray`/`AutoTArray<nsCSSValue,64>` at 4 `nsRuleNode.cpp` sites + `nsDebugImpl::Break` = **genuine root-cause removal** (deleting the dynamic alloca kills both `splitFramePointerPush` and `hasBasePointer`).
  - libffi `ffi_call_int` `optnone` = **layout luck, NOT trigger removal** — `[read-in-source]`-consistent with `llvm/lib/CodeGen/TargetPassConfig.cpp:1098-1104`, where `LocalStackSlotAllocation` runs *because* the opt level is None. A libffi bump can put a victim back in the 168–255-byte FP window with `optnone` still faithfully applied.
  - source-vigilance grep + `-Wvla-extension` pass (a runtime-sized `T x[n]` is not grep-detectable).
- **WHAT WOULD CLOSE IT:** `HANDOFF-TO-VARAN.md` **H4** (relink on rt1 with every source workaround still in place — one variable at a time) then **H7 item 1** (remove the `optnone` lever and **re-verify the frame layout**, not merely that the attribute is present). Results land in `RT-CLANG-ACCEPT-1-RESULTS.md`.

### D11 — #6, musttail vararg + `va_start` fatal · **FIXED-BY-PATCH-0007**

> **MOVED TO FIXED-BY-PATCH-0007, 2026-08-10.** V4 (the one condition that had kept this row OPEN)
> is now MET: H-VA returned GREEN on hardware 2026-08-09 — 11/11 cases exit 0, the must-fail
> companion failing case 7 and ONLY case 7 (exit 1). Oracle: `scratch/T8/ACCEPTANCE-0007.md` V1–V4.
> Everything below is the state of the row as it stood before that result, kept for the audit
> trail (same convention as D03's block above).

- `[read-in-source]` the fatal, `ARMISelLowering.cpp:2423-2425` (ARM backend, in this project's `llvm-project` checkout) at `345ce564e`:
  ```cpp
  if (!isTailCall && CLI.CB && CLI.CB->isMustTailCall())
    report_fatal_error("failed to perform tail call elimination on a call "
                       "site marked musttail");
  ```
  (Catalog says `:2424`; that is the `report_fatal_error` line itself. `main` = `:2098`.) Note this is the **generic** musttail-failure guard, not a `va_start`-specific one — the defect is whatever clears `isTailCall`.
- **WHY OPEN:** the disposition **CHANGED on 2026-08-05** under working rule 12 — a confirmed defect gets both an rt1 patch and an upstream draft, as additive tracks, never alternatives. It was "file upstream, do not implement" (no consumer could validate a fix); it is now **rt1 patch 0007 AND the filing**. `[measured]`: `patches/` contains 0001–0006 only — **0007 does not exist**. Recon was in flight under an internal tracking tag **T8**, in a report that does not ship; probe inputs are banked at `scratch/T4-6/` (`fwd.ll`, `fwd2.ll`, `fwd3named.ll`, `fwd4named.ll`, `fwd_nomusttail.ll`, `fwd_novastart.ll`, `c6.c`) `[measured]`.
- Not hit in the Varan tree: the Bug-1 vPMF thunks are variadic `musttail` forwarders **without** `llvm.va_start` (control: the same grep fires twice on a TU that really calls it), so they took the wrong-code path instead.
- Upstream: **UNFIXED on `main`**; AArch64 compiles the identical IR — the built-in control. Draft ready: an upstream filing prepared but **NOT YET FILED** (19,188 bytes) `[measured]`. → D36.
- Also documented as a README known limitation (an upstream filing prepared but **NOT YET FILED** §3), including that under LTO the fatal moves from compile time to **link** time and that `clang-cl -flto -c` still rejects the source spelling in the front end (`error: 'musttail' attribute may not be used with variadic functions`) — the exposure stays IR-level.
- **WHAT WOULD CLOSE IT:** T8 lands 0007 with an A/B oracle (must-fail control = stock 18.1.8 still fatal) + a lit test, and the filing is made.

### D12 — #7, `-Wpadded` dead under MS layout · FIXED-BY-PATCH-0006

- Patch: `patches/0006-clang-ms-layout-padding-diagnostics.patch`, 12,214 bytes; commit `345ce564e` `[measured]`.
- `[read-in-source]` the wiring, `clang/lib/AST/RecordLayoutBuilder.cpp` at `345ce564e`: free function `:2280`, Itanium forwarder `:2324/:2327`, and the three Microsoft-builder call sites at **`:3016`, `:3072`, `:3103`** — structurally identical to LLVM 21 (`upstream-check/RLB.release_21.x.cpp` `:3012/:3068/:3099`).
- Oracles (the project's working log):
  - diagnostic fires: stock 18.1.8 **0** → rt1+0006 **7**, matching the clang-21 preview target;
  - **corpus, finding-for-finding**: baseline stock clang 21 = **1355 hits / 2582 TUs / 80 distinct sites**; rt1+0006 = **1355 / 2582 / 80**; **differing lines 0**; compiled 2582/2582 on both sides. Controls: piloted on a TU clang-21 is known to flag (`icu_78::Calendar`) with byte-identical hits, and dropping one baseline line makes the comparison report exactly 1 difference — so it can detect one;
  - **hard constraint held**: default builds byte-identical (identical SHA, 765 B) while the same pair differs 0 vs 7 with the flags on;
  - lit 6/6.
- This is the only catalog defect a toolchain bump resolves (fixed in released LLVM 21) — rt1 backports it anyway because rt1's consumers are on 18.
- Nothing to file upstream (already fixed in a shipping release).

### D13 — `-fdump-record-layouts-complete` crashes clang 18 · **FIXED-BY-PATCH-0008**

> **MOVED TO FIXED-BY-PATCH-0008, 2026-08-10.** T9a (below) named the crash site and the upstream
> fix (`e4882d83d77f`, first shipped LLVM 19, never backported to 18.x). 0008 is a verbatim port,
> commit `7653a13d8` (amended from `bed948385`); `build/bin/clang.exe` is rebuilt at `7653a13d8`
> and re-run — the STOP condition that had held the rebuild is CLEARED. Everything below is the
> state of the row as it stood before the patch landed, kept for the audit trail.

**`[measured]` — measured this session, with the flag-absent control and the clang-21 control:**

Repro, one line (`a4.cpp`, this project's working tree, outside the shipped `scratch/`):
```cpp
template <class T> struct Tpl { T a; int b; };
```
Command: `<clang> -cc1 -triple thumbv7-unknown-windows-msvc -fdump-record-layouts-complete -emit-obj -o a4x.o a4.cpp`

| compiler | with the flag | without the flag |
|---|---|---|
| `clang version 18.1.8` (the stock, unpatched reference install) | **rc=139, Segmentation fault** | rc=0 |
| `Varan clang version 18.1.8-rt1 (…345ce564e…)` | **rc=139, Segmentation fault** | rc=0 |
| `clang version 21.1.8` (`clang21\pkg`) | rc=0 | — |

Bisect `[measured]`: `struct Plain { int x; char c; };` → rc=0 · `struct Fwd; struct Holder { Fwd *p; int q; };` → rc=0 · a **class template** (instantiated or not) → rc=139. The trigger is the class template.

- Independently reproduces the project's working log's three-way attribution (stock clang 21 clean; rt1 pre-0006 `3afb49879` crash; rt1 +0006 `345ce564e` crash — **identical**), i.e. the crash is **pre-existing in the 18.1.8 base** and patch 0006 neither causes nor changes it.
- Consequence already paid: LAYOUT-AUDIT pass 2 (forced layout of every record) is **not a runnable oracle on any 18-based compiler** — 177 of 185 selected TUs crashed. Pass 1 (2,582 TUs) stands as the oracle; pass 2 is BLOCKED with its cause named.
- **WHY OPEN:** recon is in flight as **T9a** (`scratch\T9a\` exists and is empty as of this session `[measured]`). The crash site has not been named in any banked report, no upstream ledger entry exists for it, and no verdict has been recorded — so under this table's own rule it is OPEN, not "low value".
- **WHAT WOULD CLOSE IT:** T9a names the crash site in the 18.1.8 tree, identifies the upstream commit that fixed it before 21 (the banked `upstream-check/RLB.release_21.x.cpp` may not be the right file — no network is available, so if the fix is elsewhere, say so rather than invent it), and returns a disposition: rt1 patch 0007-series + filing per rule 12, or NOT-A-BUG-for-rt1 with the measurement that settles it (e.g. flag is `-cc1`-only and unreachable from any production driver line — that argument is **not** yet made anywhere).

### D14 — `__declspec(align(K))` below natural alignment inside `#pragma pack(P)` · **OPEN**

- Minimised divergence (the project's working log):
  ```cpp
  #pragma pack(4)
  struct __declspec(align(2)) LowAlign { double d; };
  // clang: alignof 8, sizeof 16    MSVC: alignof 4, sizeof 12
  ```
- **10 of 12,000** fuzz shapes. Re-confirmed 10/10 by a second oracle touching **no layout dump** (`ShowSize<N>` + `__builtin_offsetof`), so it is not an artefact of `/d1reportAllClassLayout`.
- **Not an rt1 regression:** stock 18.1.8, stock 21.1.8 and rt1 emit a **byte-identical value vector**. Upstream clang behaviour.
- MSVC is internally inconsistent: it emits **C4359** saying the specifier "will be ignored", then its measured `alignof` **is** that specifier's value. "Match MSVC" is therefore not automatically the right target.
- **WHY OPEN:** the T2 STOP condition fired here and was honored literally — triage was forbidden, so none was done. `LAYOUT-FUZZ.md` was deliberately **not** written because its stated precondition (zero divergences) is not met.
- **WHAT WOULD CLOSE IT:** `HANDOFF-TO-VARAN.md` **H-ALIGN** — a Varan-side count with a shipping/non-shipping split, searched with a demonstrably armed regex (a planted case is acceptable; a bare "none found" is refused as gate-vacuity in grep form). The decision table is pre-agreed: **0 instances or non-shipping only** → rt1 documents it, an upstream filing prepared but **NOT YET FILED** §1 loses its `TBD-pending-Varan-grep` tag, **no patch**; **≥1 shipping instance** → open a real recon for a candidate 0007 with that instance as the validation consumer. Rationale for the high bar: a 0007 here changes record layout for *every* TU putting an align-carrying type inside a pack region — far wider than 0001–0006, all of which are narrow.

### D41 — NEW ROW, opened 2026-08-30 — PR #184953 is not self-contained for backporting · **RECORDED, NOTHING TO FILE**

> ⚠ **This row was numbered D16 by mistake when it was written (BATCH RT1.1-2) and is renumbered to
> D41 here.** D16 was already taken by *"`__restrict` is part of the MSVC name mangling"* — a
> different defect with a different verdict — so the draft carried **two `### D16` sections**, which
> is precisely what a table promising "every defect with exactly one verdict" cannot have. D39 and
> D40 were also already in use (flexible-array union; the thunk-gate halfword read, cited from
> `RELEASE-NOTES-draft.md:335`), so **D41 is the first free number**. Like D39 and D40 this is a
> NEW ROW outside the 38-row master table, so no tally changes.

- **Symptom.** Upstream `6c34ed7b3` writes `[(cleanupret bb)]` in `ARMInstrInfo.td`, which needs
  main's `SDTCleanupret : SDTypeProfile<0,1>`. LLVM 18.1.8 declares `cleanupret` with **`SDTNone`,
  zero operands** (`TargetSelectionDAG.td:644`), so the port fails TableGen before compiling
  anything: *"In CLEANUPRET: cleanupret node requires exactly 0 operands!"*
- **Verdict: VERSION SKEW, NOT A DEFECT.** On main the arity is self-consistent. The incompatibility
  exists only when the patch moves to a tree predating the arity change, so there is **nothing to
  file upstream** and this must not be re-opened as an owed filing under working rule 12.
- **rt1's action.** Patch 0009 writes `[(cleanupret)]`, using in-tree precedent from the same tree:
  `AArch64InstrInfo.td:4851` and `X86InstrCompiler.td:198`. `catchret` needs no change - 18's
  `SDTCatchret` is already `<0,2>`. Three further divergences in the ported test IR (`inbounds nuw`
  GEPs x24, `captures(none)` x2, `llvm.lifetime.*` size operand) were adapted the same way.
- Full note: `scratch/T8/CLEANUPRET-NOTE.md`.

### D42 — NEW ROW, opened 2026-09-08 — ARM32 Windows `setjmp` is handed the FRAME POINTER, not the entry stack pointer · **FIXED IN rt1.2 (patch 0010)**

> Like D39–D41 and D43 this is a **NEW ROW outside the 38-row master table, so no tally changes.**

- **The site**, READ-IN-SOURCE. `clang/lib/CodeGen/CGBuiltin.cpp`, `EmitMSVCRTSetJmp`. On Windows
  `_setjmp`/`_setjmpex` take a second argument — the frame — which the CRT stores into the `jmp_buf`
  and which `longjmp` later hands to `RtlUnwindEx` as the frame to unwind to. clang computes it with
  `llvm.sponentry` (the stack pointer as it was on entry) **only when the architecture is aarch64**;
  32-bit x86 goes to `_setjmp3`, and every other case — 32-bit ARM included — falls through to
  `llvm.frameaddress(0)` and passes the frame pointer.

- **Why the frame pointer is the wrong value on ARM32.** The frame pointer is `r11`, and a function
  that sets one up leaves it pointing at its own saved slot. `r11` and `lr` are the two
  highest-numbered registers in a callee-save push, so that slot is the second from the top of the
  push — 8 bytes below the entry stack pointer when the push is the first prologue instruction, and
  further once the prologue has moved SP. MSVC for the same target passes the entry stack pointer.

- **MEASURED on hardware — the DEFECT, not the fix.** The device A/B in `TRIP4-ANALYSIS.md` §5:
  `lua-msvc` runs to completion, `lua-clang` dies **`0xC0000028` (STATUS_BAD_STACK)** on a `longjmp`,
  on real ARM32 Windows. Four perturbations of the stored frame value all die with the same status
  (`scratch/SJ1/SJ1-SECTION1-RESULTS.md` §12), which is what identifies the stored value as the
  cause rather than a coincidence.

- **MEASURED in the compiler, this session** (`scratch/RT23P/probe_all.py`, probe 0010, `-cc1
  -triple thumbv7-windows-msvc` over `clang/test/CodeGen/ms-setjmp.c`): stock 18.1.8 emits
  `llvm.frameaddress` ×3 and `llvm.sponentry` ×0; rt1.2 emits `llvm.sponentry` ×3 and
  `llvm.frameaddress` ×0. Stock 23.1.0 and 23.1.1 still emit `llvm.frameaddress` — **upstream has
  not fixed this in any released clang.**

- **No backend work was needed.** `__builtin_sponentry` already exists for ARM,
  `ARMTargetLowering::LowerSPONENTRY` already lowers it to the entry stack pointer, and
  `llvm/test/CodeGen/ARM/sponentry.ll` already runs `llc -mtriple=thumbv7-windows-msvc` over IR that
  hands `llvm.sponentry` to `_setjmpex`. Only the frontend condition was left behind.

- **rt1's action.** Patch **0010** extends the condition to 32-bit ARM, leaving the AArch64 half
  spelled `getArch() == Triple::aarch64` rather than `isAArch64()` so the change is a **pure
  extension** — `isAArch64()` also matches `aarch64_be`, which clang today compiles with
  `llvm.frameaddress`, so that spelling would silently change a target this patch has no business
  touching.

- **Upstream.** A PR package is prepared at `upstream/PR-D42-arm32-windows-setjmp-sponentry.md`
  with the patch at `upstream/patches/0001-D42-arm32-windows-setjmp-sponentry.patch`. **Not filed —
  filing is the user's action (working rule 11).**

- ⚠ **The FIX has not run on ARM32 hardware.** `BATCH-SETJMP-1-AMEND-2.md` A1 removed the device
  trip from that batch; `SETJMP-1-RESULTS.md` records "Nothing here has run on hardware." The defect
  is hardware-MEASURED, the fix is compiler-MEASURED only. See D42 in the release notes, which says
  the same thing in the same words.

### D43 — NEW ROW, opened 2026-09-07 — clang's `BI_setjmp` dispatch upgrades `_setjmp` to `_setjmpex` on **AArch64 only**; ARM32 emits `_setjmp` · **DISCLOSE, NO PATCH**

> Like D39, D40 and D41 this is a **NEW ROW outside the 38-row master table, so no tally changes.**
> Deliberate, not an omission: the OPEN count is a shipping number carried at five sites in this file
> and in the frozen `stage/` copy, and this table already records under D37 that moving it is the
> user's decision and not a side effect of adding a cross-reference.
>
> **D42 is the row immediately above**, added for rt1.2. It was reserved in `BATCH-SETJMP-1.md`
> §0.6 as the free D-number for the `setjmp` frame-value defect; D43 was opened first, before it,
> because `BATCH-UPSTREAM-3-AMEND-1.md` A2 asked for it by that number.

- **The site**, READ-IN-SOURCE at two named trees. `clang/lib/CodeGen/CGBuiltin.cpp`,
  `case Builtin::BI_setjmp:` — rt1 tree `60876c5f8` lines **5222–5229**; upstream `main` at
  **`edbf358d0`** lines **6176–6185** (worktree `scratch/UP3/main-src`). Identical shape in both:

  ```cpp
        if (getTarget().getTriple().getArch() == llvm::Triple::x86)
          return EmitMSVCRTSetJmp(*this, MSVCSetJmpKind::_setjmp3, E);
        else if (getTarget().getTriple().getArch() == llvm::Triple::aarch64)
          return EmitMSVCRTSetJmp(*this, MSVCSetJmpKind::_setjmpex, E);
        return EmitMSVCRTSetJmp(*this, MSVCSetJmpKind::_setjmp, E);
  ```

  AArch64 **upgrades** the call to `_setjmpex`; 32-bit ARM falls through to `_setjmp`. MEASURED in
  the emitted IR with stock clang 22.1.8 (`clang22\pkg\bin\clang.exe`, sha256 `986af49c2d1eefea…`),
  `-cc1 -triple thumbv7-windows-msvc`: `call arm_aapcs_vfpcc i32 @_setjmp(ptr @jb, ptr %0)`, against
  aarch64's `@_setjmpex`.

- **Why it is inert on ARM32 — and this is the cheap form of the argument, checkable from two header
  lines.** MSVC's own header maps `setjmp` to `_setjmp` on **every** architecture unless
  `<setjmpex.h>` is included. MEASURED on the pinned toolset:
  `D:\Program Files\Vscom\VC\Tools\MSVC\14.16.27023\include\setjmp.h:150-151` —
  `#ifndef _INC_SETJMPEX` / `#define setjmp _setjmp`; and `setjmpex.h:18-19` — `#undef setjmp` /
  `#define setjmp _setjmpex`, in the `#else` of the `_M_IX86` test at `:14`. **So on ARM32 clang
  calls exactly what MSVC calls.** AArch64's upgrade is the deliberate deviation from the header;
  ARM32's non-upgrade is not a deviation at all.

- **Corroborating runtime measurement, cited rather than re-run.** `BATCH-SETJMP-1.md` §0.5 and
  `BATCH-UPSTREAM-3-AMEND-1.md` A2: in the shipped `lua-clang.exe` the `bl` reaches `setjmp`, whose
  body is a check of `_setjmpexused` followed by an indirect tail-branch into `setjmpex`;
  `_setjmpexused` was read from both PEs and is non-zero in both; `setjmpex`'s first instruction is
  `str r1,[r0]`. **The ARM32 CRT routes `_setjmp` into `_setjmpex` at runtime**, so the frame value
  reaches `jmp_buf.Frame` either way. ⚠ **NOT re-derived in this session**: the shipped PEs are
  stripped — `llvm-objdump -d --triple=thumbv7-unknown-windows-msvc lua-clang.exe` yields 101,456
  lines and **zero** `setjmp` symbol hits — so reproducing it needs the map or PDB the earlier
  session worked from.

- **Disposition: DISCLOSE, no patch, and specifically NOT BUNDLED into the D42 PR.** One logical
  change per PR; a second behavioural change folded into a one-line intrinsic fix is how a small
  reviewable patch turns into a long argument. It is instead **named in the D42 PR's follow-up
  comment**, because a reviewer who opens that function will see the second predicate, and it is
  better that the author named it and said why it is out of scope than that the reviewer found it.

### D15 - compiler-rt builtins gap / `__aeabi_{u,}idivmod` * **CLOSED 2026-08-30: KEEP THE SHIM**

- **VERDICT (scratch/W3/D15-VERDICT.md): keep `aeabi-shim.c`; rt1.1 ships no builtins archive.** This confirms rather than changes what rt1 shipped - `RELEASE-NOTES.md:60-62` already records that rt1 ships no builtins archive, gated off by `scratch/W3/div0_check.py` which fails it by design.
- **The catalog's MECHANISM was wrong and is corrected** (the conclusion, supply a shim, stands). It said clang emits the combined EABI divmod helpers for the no-hardware-divide Cortex-A9. MEASURED with an armed control, same source and same `-mcpu=cortex-a9`: `thumbv7-unknown-windows-msvc` emits `__rt_sdiv`/`__rt_udiv` ONLY, while `thumbv7-none-eabi` and `armv7-none-eabi` emit the full `__aeabi_*` family. The helper family is chosen by the TRIPLE'S ENVIRONMENT, not by hardware-divide capability. The gap bites only source that NAMES the symbols - in Varan, `wasm/WasmTypes.cpp:306` takes the ADDRESS of `__aeabi_idivmod`, surviving `JS_CODEGEN_NONE`.
- **Both CMake gates MOVE** (banked at `patches/candidates/`), so the gates were never the blocker. The reason to decline is that compiler-rt's divide-by-zero DOES NOT TRAP where MSVC's `__rt_*` does, and its remainder out-parameter is never written - a silent regression in exchange for two symbols compiler-generated code on this target never asks for.
- The A32 fear is **REFUTED**: `compiler-rt/lib/builtins/assembly.h:141-143` keys code state off `__thumb2__`/`__thumb__` and emits `.thumb`; no `arm/*.S` contains `.arm`/`.code 32`/`.syntax divided`; six were assembled successfully.
- Two named CMake gates (`RT-CLANG-RECON-1.md` §6 R5.3): `compiler-rt/lib/builtins/CMakeLists.txt:527-553` sets `arm_SOURCES` only `if(MINGW)`/`elseif(NOT WIN32)` — for WIN32-non-MINGW there are **no ARM sources at all**; and `builtin-config-ix.cmake:53`'s ARM32 list has `armv7` but **not `thumbv7`**. Naming subtlety: for arch `armv7` the output is `clang_rt.builtins-arm.lib`, but the driver on a **thumb** triple looks for `clang_rt.builtins-thumb…` (`Triple.cpp:80`, `ToolChain.cpp:562-574`).
- **THE SHIM SHIPS IN THE rt1.1 PACKAGE.** `runtime/` carries `aeabi-shim.c` (2,858 B) plus a **prebuilt** `aeabi-shim.lib` (1,814 B) and `aeabi-shim.obj` (1,466 B) built by rt1.1's own `clang-cl` for `thumbv7-unknown-windows-msvc`, and `README-aeabi-shim.txt` stating when it applies. These are the only ARM32 **target** binaries in the package. MEASURED with `llvm-nm`: it defines `__aeabi_idiv`, `__aeabi_idivmod`, `__aeabi_uidiv`, `__aeabi_uidivmod` and needs only `__rt_sdiv` / `__rt_udiv` from the MSVC ARM CRT. Only 2 of the 4 are referenced by real code we have seen. **It is opt-in** — nothing in the package links it for you, because adding it changes divide-by-zero to a `__brkdiv0` trap. Under rt1 1.0 the shim was Varan-side only, so porters knew about the gap but could not obtain the fix; that is what changed.
- ~~**WHY OPEN:** recon in flight as T9b…~~ **SUPERSEDED — this bullet described the rt1 1.0 state and is no longer true.** T9b returned; the verdict is the CLOSED one in this section's header. rt1.1 still ships **no builtins library** — that part stands and is deliberate — but it now **does** ship the shim, which is what the gap actually needed.
- **WHAT CLOSED IT:** T9b returned outcome (b) below — the shim is sufficient and the library would be a silent regression. Recorded for the record, the two branches that were on offer were: (a) a scoped rt1 change (third branch at `CMakeLists.txt:527` for WIN32-non-MINGW + `thumbv7` in `builtin-config-ix.cmake` + the `-thumb` naming), validated by an oracle that a `thumbv7-windows-msvc` link resolves `__aeabi_idivmod` **with the shim removed** and a must-fail control proving it fails without; or (b) NOT-A-BUG/out-of-scope with the measurement (e.g. the shim is sufficient and the library would be unused), plus the decision recorded in the README.

### D16 — `__restrict` in the MSVC mangling · NOT-A-BUG

- MSVC encodes `__restrict` on a pointer parameter into the decorated name; clang-cl matches it for ABI compatibility. A declaration and a definition differing only in `__restrict` are **two different symbols**, invisible until link time. GNU-mangling builds never see it (Itanium does not encode restrict).
- Worked example: `gfx/skia/.../SkBitmapProcState.cpp` vs the definition generated through `SkBitmapProcState_procs.h`:
  `defined: ?SI8_opaque_D32_filter_DX_neon@@YAXABUSkBitmapProcState@@P I BIHP I AI@Z` vs `wanted: …P BIHP AI@Z` — the `I` between `P` and the CV letter is the restrict qualifier.
- **The dangerous part is the misdiagnosis, not the defect:** an undefined `*_neon` symbol looks exactly like an incomplete NEON source list, and restoring a `-U__ARM_NEON__` workaround makes the link succeed by **silently reverting the library to scalar**. Confirm with `llvm-nm` that the symbol is defined (`T`) but differently mangled before touching any source list.
- ABI conformance. **No upstream fix will ever come**; remedy lives in our source. Not to be filed.

### D17 — MSVC signed unscoped enums · NOT-A-BUG

- MSVC (and clang-cl in MS-ABI mode) types an unscoped enum with no fixed base as **signed `int` always**; GCC/Clang in GNU mode pick unsigned when every enumerator is non-negative. Consequences measured on this toolchain: `enum RegType{…Int=3}` in `kind:2` reads back **−1**; `Condition Always=0xe0000000`, `cond >> 28` sign-extends to `0xfffffffe` not `0xe`.
- **WAI per the MS enum ABI** — never "fixed upstream", hits any MSVC-targeting build.
- Remedy is a source gate, not a toolchain change: `-Werror=signed-enum-bitfield` + `-Werror=bitfield-constant-conversion` (both verified to catch the `RegType` case), plus `static_assert(std::is_unsigned<std::underlying_type<E>::type>::value)` for the shift case.
- **Upstream thread, recorded so nobody re-searches it: `llvm/llvm-project#119228` — *"enum unhelpfully uses signed underlying type"*** (open since 2024-12-09, label `clang:diagnostics`, 5 comments, all about **bit-fields**). **No diagnostic patch is authored here** — that would be invention, and rt1 ports rather than invents. **And no comment is posted either:** see the next bullet. Draft, marked WITHDRAWN with the reasoning, at `upstream/COMMENT-enum-shift-issue-119228.md`.
- **⚠ THE "NO DIAGNOSTIC EXISTS" PREMISE IS REFUTED. MEASURED 2026-08-31 on clang 22.1.8** (`scratch/UP2/enum-shift/D17-SHIFT-MEASURED.md`), with an armed control. A first pass here claimed the shift form was undiagnosed below `-Weverything`; it had only tried `-Wall -Wextra`. In fact **`-Wmicrosoft-enum-value` fires under `-Wpedantic` alone** (also `-pedantic`, `-Wmicrosoft`, `-Wall -Wextra -Wpedantic`) and is a **hard error under `-pedantic-errors`**; only the bare default and `-Wall -Wextra` are silent. **Its coverage is EXACT, not partial:** across five enumerator shapes the MS/GNU divergence occurs *iff* the enumerator does not fit in `int`, which is *iff* the warning fires (`0xe0000000`, `0x80000000` diverge and warn; `0x7fffffff`, `0x40000000`, `14` do neither). The earlier framing — "it only fires when an enumerator is out of range", offered as a weakness — was backwards: that is the bug's own precondition.
- **⚠ KNOWN-STALE SITE IN THE FROZEN COPY, recorded so the next reader does not re-derive it.** `stage/DISPOSITION-TABLE.md:209` (and its `dist/` twin) still reads *"two clang diagnostics already exist and catch it"*. For the **shift** form neither of those two applies — both are bit-field-scoped; the one that catches it is a **third**, `-Wmicrosoft-enum-value`. The frozen copies are **deliberately untouched** (rt1 as released stays frozen); this line is the record that the divergence is intentional and where it lives.
- **Consequence for the remedy, and it is an improvement.** The line above prescribes a per-site `static_assert`. **`-Werror=microsoft-enum-value` catches the whole shift class at once**, at the enumerator's definition rather than at every use — a compiler flag rather than a code change. The bit-field half is unchanged (`-Werror=signed-enum-bitfield` + `-Werror=bitfield-constant-conversion`, both of which fire on assignment into the bit-field, not on reading it).
- **Do not merge with D05/D12:** both warnings live in `AnalyzeBitFieldAssignment` (`SemaChecking.cpp:14999`) — assignment/initialiser **value** checks that can never fire on a layout trap. rt1 decision (`RT-CLANG-RECON-1.md` §11 R7.2): **do not default-enable either** — `-Wbitfield-constant-conversion` is already on by default on this target, and promoting them measured 313 failures in `js/src` alone / 336 link-breaking warnings / ~20 ICU errors / 375 live diagnostics.

### D18 — A32 on Windows RT · OS/PLATFORM-HAZARD

- **What it actually is:** the RT kernel does not preserve `CPSR.T` across a context switch into A32 code, so an A32 stub faults `0xC000001D` **intermittently, after preemption**. It builds and passes every static check.
- **clang is correct** — it emits `blx` for interworking. There is no compiler defect and no compiler fix; this is not filable and no patch can address it.
- Consequences, which is why it is in the table rather than in a footnote: **THUMB-2 ONLY** for everything, verified by disassembly and by a standing dialect gate; and the **A32 JIT is structurally impossible** → `--disable-ion` / `JS_CODEGEN_NONE`, interpreter only. This is the project's central constraint.

### D19 — `alloca` 4×-undersize hypothesis · NOT-A-BUG

- REFUTED as an undersize bug: `alloca(nprops*sizeof(nsCSSValue))` computes `r4=(gPropertyCountInStruct[Font]<<1)` and passes it to `__chkstk`, whose first instruction is `subs.w ip, sp, r4, lsl #2` — **`__chkstk` takes `r4` in WORDS**, so `(27<<1)=54` words = **216 bytes = 27 × `sizeof(nsCSSValue)`, exactly correct**.
- The alloca's *presence* was nevertheless the D09 trigger (it sets `hasVarSizedObjects`, satisfying **both** Bug-5 preconditions at once) — which is why removing it was right for a different reason than the one first proposed. Listed as its own row so nobody re-chases it.

### D20 — `js::jit::Operand` 12 vs 8 · NOT-A-BUG

- MEASURED, replica `S_Operand` in `scratch/F06/jitarm_layout.cpp`: **MS 12 / Itanium 8**, reported 54 times. Site `uxp/js/src/jit/arm/Assembler-arm.h:1160-1170`: `enum class Tag : uint8_t` (1-byte unit) beside `uint32_t reg_ : 5` (4-byte unit) → per the D05 size rule a new allocation unit opens.
- **Counterfactual measured in the same run:** the identical class with `enum class Tag : uint32_t` is **8/8** — the underlying type is the whole cause.
- Upstream-unmodified: `git show 659c690d:js/src/jit/arm/Assembler-arm.h` line 1040 already reads `enum class Tag : uint8_t {`. Varan did not introduce it.
- **Not a trap:** no `sizeof(Operand)`, no `offsetof` on it, no `memcpy`, no union, no serialisation, no assertion. Cost = 4 wasted bytes per instance of a transient by-value argument type. **Recorded, not fixed** — and `HANDOFF-TO-VARAN.md` H3 explicitly leaves it untouched so nobody "fixes" it into a gratuitous upstream divergence.

### D21 — the other 30 MS-layout padding sites · NOT-A-BUG

- Denominator: **2,582 TUs, 31 distinct diagnostic sites, 0 compile failures, 0 real traps** (`LAYOUT-AUDIT.md` §5.3/§6).
- Trap criterion was stated **before** triage: (a) something depends on size/byte layout, or (b) the declaration is compiled under the MS ABI for the first time. (a) MEASURED absent for all 31 — **no `sizeof(...)` assertion exists on any of them**; every consumer uses `offsetof`. (b) satisfied by exactly one site = D20.
- Three of the 31 are measured **not to diverge at all** (`nsStyleSet`, `NameLocation`, `WebSocketChannel`) — the empirical basis for "a `-Wpadded-bitfield` hit is not by itself a divergence, let alone a trap".
- The two that sit on real interfaces are safe **for a stated reason**, and are the named re-check points if that reason ever changes: `SSLCipherSuiteInfoStr` (`security/nss/lib/ssl/sslt.h:491`) is a genuine cross-module ABI struct, safe only because NSS and its sole consumer are compiled by the same clang-cl and **no foreign-ABI binary links our `nss3.dll` on Windows RT**; `js::wasm::CodeRange` (`js/src/wasm/WasmCode.h:251-261`) **is** a serialisation format, safe only because the wasm cache is build-scoped by a `buildId` comparison (`WasmTypes.h:867-886`).
- Also closes the catalog's checklist item 4 (`:301`, "this audit had never actually been performed"): **PERFORMED**, scope corrected to *bitfield storage-unit size*, not `bool`.

### D22 — LAYOUT-FUZZ corpus gap · **OPEN**

- Named gap, in the project's working log: the 12,000-shape corpus has **no inheritance, no virtual functions and no vtables — the MS ABI is at its most distinctive exactly there.** Second named gap: divergence count is generator-weight dependent (860 of 12,000 shapes carried the align trigger combination).
- **WHY OPEN:** D05's verdict is fully supported *on the bitfield axis*, which is what the experiment was built to settle. It is not evidence about vbases/vtordisp/vtable-pointer placement, and no other measurement in this campaign covers them.
- **WHAT WOULD CLOSE IT:** extend the generator with single/multiple/virtual inheritance and virtual functions, re-run the same rt1-clang-cl vs MSVC-14.16-ARM field-for-field comparison with the same armed driver floor (Itanium target → non-zero divergences), and report. Any divergence there is a new confirmed defect and a patch candidate under the same STOP rule.

### D23 — clang-cl driver argument spellings · NOT-A-BUG

- `-O0` is **silently dropped** by clang-cl (only `/O[12xd]` are recognised) — so production `/O1` is `cc1 -Os`, and every opt-level claim across the catalog should read `-Os`. This is what settled D08.
- `-g0` is **rejected as `-Wunknown-argument`** under the clang-cl driver, so `-Zi` survives and the Bug-4 ICE persists; `-gline-tables-only` is the working per-TU lever. Correction carried: this is *not* a `-Qunused-arguments` effect — `-g0` is not accepted at all, so it cannot be made to work by adjusting warning flags.
- Documented driver behaviour, not a defect. Listed because it cost two measurement lanes and one wrong root-cause attribution.

### D24 — `d3dcompiler_47.dll` census blind spot · NOT-A-BUG

- No PDB, no map → no name-based enumeration. A blind byte-shape sweep finds 242 `ldr rA,[Rn]; ldr rB,[rA,#i]; bx rB` sequences; **of those loading through `r0` (the `this`-based vcall shape), 186 use r12 and 0 use an argument register**. The shape-B sweep finds 1 hit, unadjudicable without a signature and left that way. Sweep sensitivity control: 3/3 in `vctrl.dll`, 1/1 in `vctrlB.dll`.
- **The settling measurement:** the DLL is a prebuilt MS redist **built by MSVC in 2017**, so a clang allocator defect cannot be present in it by construction. It is also excluded from `varan-imp-fix.py` by `is_ours()` (1,167 benign even pointers).
- Recorded corollary that is *not* a verdict about this DLL but about method: a blind sweep is useless as a gate — the same sweep reports 1,274 argument-register shape-A hits in REL `xul.dll`, essentially all ordinary virtual tail-dispatch.

### D25 — PDB-publics blind spot · **OPEN**

- Quantified: on the two PEs that have both a map and a PDB, PDB-publics recall of the map's thunk set is **96.34 % on `xul.dll`** (156 addresses map-only) and **100 % on `libGLESv2.dll`**. All 156 are **adjustor thunks of anonymous-namespace classes** — static COMDATs, therefore not publics.
- **WHY OPEN:** each of the **17 PDB-only PEs** carries a blind spot of the same kind, bounded at roughly 4 % of its thunk population — *bounded by inference from two PEs, not enumerated on the other 17*. `xul.dll` + `libGLESv2.dll` hold 4,286 of the fleet's 4,334 thunks and are covered map ∪ PDB with 0 gap, which is why the residual is small — but it is not zero and it has no verdict.
- **WHAT WOULD CLOSE IT:** the `FLEET-CENSUS.md` §9 gate extension (PE-driven recursive population + dbghelp `[thunk]:` classification) applied to the 17, or a map emitted for them. Varan-side (**H1**).

### D26 — `gate-thunks.py --expect-min` floor · **ARMED — DEMONSTRATION OWED**

> **2026-08-10: NOT CLOSED.** A prior pass here wrote "CLOSED by F0.2" on the strength of a
> comment inside `gate-thunks.py` asserting the demonstration, not a record of it. This row's own
> closure criterion, below, has always required **both directions demonstrated** — "a floor that
> has never been shown to fire is not armed." A comment is not a transcript. Downgraded to ARMED.

- Gate-vacuity instance **#11**, **true only before 2026-08-04**: at that time grep found exactly two hits for `--expect-min`, both inside the script itself; no caller passed it, so the effective floor was **1** and a thunk count that collapsed to nothing would still print PASS.
- **RE-MEASURED 2026-08-10** in the Varan tooling tree (the canonical tooling home the catalog names; the older copy of `gate-thunks.py`, in the Varan-source tooling tree, lacks `--expect-min` entirely — `grep -c` returns 0 — and is not authority here; byte-identical banked copies live at `scratch/D26/banked-tooling/`, see its `PROVENANCE.md`): both production callers now pass the floor. `varan-interwork/run-suite.sh` and `varan-thunk-override/varan-fixup.sh` each call `python3 "$GT/gate-thunks.py" "$OBJ" --expect-min 178 --class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19 --max-review 844`. `gate-thunks.py`'s F0.2 arming comment **asserts** inline: *"F0.2 (2026-08-04): the floor is now ARMED by both production callers ... Until today NO caller passed it, so the effective floor was 1 and a count collapsing 178 -> 1 still printed GATE PASS (gate-vacuity instance #11)."* This is a comment written by the change's own author, in the same file as the call — not a log, not a transcript, and not dated against the code (the Varan tooling tree is not under version control, so it cannot even be dated). `gate-thunks.py`'s "`--expect-min` needs a separate value argument" check also turns the mistyped `--expect-min=178` spelling (previously silently ignored, floor stuck at 1) into a **hard error** — that part IS a static, re-checkable fact, not a demonstration claim.
- **WHAT IS MEASURED:** the flag is present at both call sites, with the values above, since F0.2 (2026-08-04).
- **WHAT IS NOT MEASURED:** a run transcript showing the gate PASS at the census value (178) and FAIL when a count is raised above it. No such transcript is banked anywhere in this repo or in the Varan tooling tree.
- **WHAT WOULD CLOSE IT:** the Varan-side handoff — run both directions, bank the transcript under `scratch/` (tracked), and cite it here by path.

### D27 — `gate-thunks.py` class/population coverage · **ARMED — DEMONSTRATION OWED**

> **2026-08-10: NOT CLOSED.** Same defect as D26 above: a prior pass wrote "CLOSED 2026-08-09 by
> H1" on the strength of the callers' own comment ("All four floors demonstrated firing"), not a
> banked run record. Downgraded to ARMED, tracked under the same Varan-side handoff as D26.

- **True only before H1.** The gate's original MAP-based check (`gate_binary()`) globs `**/*.goanna.map` and greps one mangling (`??_9\S*\$B`), so it only ever examined `$B`, in the binaries that have maps — `browsercomps.dll` had never been in its population, and a non-recursive glob had missed it three separate times. Meanwhile D02's carrier class was real: an unprototyped `$4` thunk under an ordinary mangled name was invisible to the gate **and** to the COMDAT override generator.
- **RE-MEASURED 2026-08-10** in the Varan tooling tree: `gate-thunks.py` now carries a second, separate check, the `class_census()` function (banked byte-identical at `scratch/D26/banked-tooling/gate-thunks.py`), armed by `--class-floors`. It imports a vendored census engine (`varan-thunk-override/census/engine.py` — no banked copy exists for this one) that examines **all four** thunk families — `$B`, `$4`, `$R`, adjustor. Its population builder, `engine.build_population()`, is an explicitly **RECURSIVE** `os.walk` of `dist/bin`; the function's own docstring names the exact fix — *"a non-recursive glob missed [`browser\components\browsercomps.dll`] three separate times in the rt1 project"*. Both production call sites (banked copies `scratch/D26/banked-tooling/run-suite.sh`, `varan-fixup.sh`, each at their gate-thunks.py call) pass `--class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19 --max-review 844`. `$R==0` is asserted exactly (never `>=`), so a floor of 0 cannot pass vacuously — the trap this row originally warned about; that IS a re-checkable static fact.
- **WHAT IS MEASURED:** the four-family census engine is wired in and armed at both call sites, with the floors above, since H1 (2026-08-09).
- **WHAT IS NOT MEASURED:** the callers' comment "All four floors demonstrated firing" is the author's own assertion in the same file as the call — no log, transcript, or run record is cited on this row, and the Varan tooling tree is not under version control, so the comment cannot even be dated against the code.
- **WHAT WOULD CLOSE IT:** the same Varan-side handoff D26 owes — one run covering all four class floors in both directions.

### D28 — `split8.py` is unsound · **OPEN**

- Two independent defects, both measured: **false positives on FIXED output** (its T6 is a cross-product of escaping-FP distances against BP-path store distances with no same-object constraint — mutating the frame immediate to `0x14c` makes it fire, and `0x14c` is exactly what patch 0001 now emits); and a **false negative** — its header claims `HasAuthorSpecifiedRules` does not fire and uses that as proof its delta-8 clause is load-bearing, while the sound predicate shows it **is** a genuine carrier (fi#1, a 128-byte object whose low half resolves correctly through FP and whose high half is 8 low through BP — corruption *inside a single object*).
- rt1 side is settled: QUARANTINED, replaced by `scratch/F4/peicheck2.py` and `scratch/T3/bug5_pred.py`, whose soundness property is structural (`over = prologue_total − stackSize`; returns immediately if `over <= 0`, so it **cannot fire on a compiler whose prologue allocates the assigned frame size**).
- **WHY OPEN:** the Varan-side quarantine is not installed. Anyone using `split8.py` to check the rt1 relink will conclude the fix failed.
- **WHAT WOULD CLOSE IT:** **H2** — a banner in the script itself (so it warns at the point of use, not only in a ledger) plus a ledger line naming `peicheck2.py` as canonical. Acceptance: running it prints the banner.

### D29 — `checkfix.sh` cannot be redirected · **OPEN**

- It hardcodes `SP` to a dead session scratchpad and forwards only `$TAG`/`$FLAGS` to `flagtest.sh`. (`RT-CLANG-RECON-1.md` §9.4 also corrects its own briefing, which wrongly said it takes an override as argument 3.)
- **WHY OPEN:** it is the named Bug-5 targeted regression check (the 4 carriers must stay base-pointer-free) and cannot currently be pointed at an rt1-built object — i.e. the D09 acceptance instrument is not runnable as-is. `RT-CLANG-FIX-1.md` §0 records F0.3 as "parameterised", but the fix is Varan-side and no acceptance evidence for it exists in this folder.
- **WHAT WOULD CLOSE IT:** a path parameter, Varan-side, demonstrated by running it against an rt1-built `Unified_cpp_layout_style3.obj` during H4/H5.

### D30 — rt1 builds only ARM and X86 · NOT-A-BUG

- Measured: rt1 `clang -print-targets` reports **6** (`arm armeb thumb thumbeb x86 x86-64`) where stock 18.1.8 reports **42**. `clang-cl --target=aarch64-pc-windows-msvc -c` **fails** on rt1 (`unable to create target: 'No available targets are compatible with triple …'`) and succeeds on stock.
- Deliberate configuration (`LLVM_TARGETS_TO_BUILD=ARM;X86`), documented in an upstream filing prepared but **NOT YET FILED** §2 with the mitigation (install rt1 to a separate directory, or invoke it only for the ARM32 leg).
- Honest residual recorded there and not upgraded to a claim: whether `lld-link`'s ordinary non-LTO linking of other architectures is affected was **not measured**.

### D31 — five auxiliary binaries not rebuilt · **OPEN**

- `clang-check.exe`, `clang-repl.exe`, `clang-scan-deps.exe`, `clang-linker-wrapper.exe`, `llvm-dwp.exe` are left at stock 18.1.8. **RE-MEASURED 2026-08-10 over the full stock package** (the stock, unpatched reference install, read only): 62 `.exe` total, `grep -ac "ARM Instruction Selection"` scores non-zero on exactly **14** — the 9 rt1 replaces (`clang`, `clang++`, `clang-cl`, `clang-cpp`, `ld.lld`, `ld64.lld`, `lld-link`, `lld`, `wasm-ld`) plus these **5 unreplaced**. The earlier screen's three-control arming (`llvm-strings.exe`, `llvm-cxxfilt.exe`, `clang-format.exe`, all score zero) was real but its **enumeration missed `llvm-dwp.exe`** — the fourth binary carrying the pass string that the earlier pass never named. Re-armed with a fourth negative control: `llvm-objdump.exe` also scores zero. So they **can** reproduce the bugs rt1 fixes.
- They are separate link products; rt1's build produces none of them (`build\bin` contains none).
- **WHY OPEN:** the gap was *accepted* on the basis that they are 0-invocation in every Varan build — that is a statement about one consumer, not about the community RT ports that are rt1's second consumer.
- **WHAT WOULD CLOSE IT:** either add the five to the product target list and overlay them (cost not yet measured), or state the limitation in the shipped README as a checked precondition ("if your build invokes any of them for ARM32 codegen, rt1 does not fix your build"). The README draft already says this; the row closes when PKG-1 adopts one of the two.

### D32 — the ARM LTO path is untested · **OPEN**

- rt1's `lld` **does** carry the codegen fixes: `build.ninja` links `LLVMARMCodeGen.lib` (+ AsmParser/Desc/Disassembler/Info/Utils) into `lld.exe`, `lld-link.exe` is a byte copy made in that link's `POST_BUILD` step (grep `build.ninja` for the `cmake.exe -E copy` line that produces `lld-link.exe`/`ld.lld.exe`/`ld64.lld.exe`/`wasm-ld.exe` from `lld.exe`; `build.ninja` is generated/gitignored, so its line numbers are not stable — re-grep rather than trust one), and the patched files are listed at `llvm/lib/Target/ARM/CMakeLists.txt:36` and `:40` in the rt1 tree at `345ce564e`. Confirmed on the shipped binary by a string screen (`lld-link.exe` has the ARM pass-name string; `llvm-objdump.exe` from the same build does not).
- **WHY OPEN:** **every** rt1 oracle ran through `clang-cl`/`llc`, never through `lld-link`'s LTO code generator. Same object code is a reason to expect no difference; it is not a measurement, and this project does not ship the two as if they were the same thing.
- **WHAT WOULD CLOSE IT:** an LTO acceptance run of at least one of the three codegen oracles (0001 MIR histogram / 0003 `f8d0 c000` / 0004 no-ICE) driven through `lld-link -flto`, with the stock linker as the must-fail control. Until then the README tripwire stands: *enable LTO and you are in new territory; re-run your own acceptance from scratch.*

### D33 — lit not runnable from the product target list · NOT-A-BUG

- Measured build fact: the frozen list (`clang clang-resource-headers lld opt llc llvm-reduce FileCheck count not`) builds the shipped binaries but cannot run lit — `llvm-lit`'s config fatals on `llvm-config`, and `llvm-readobj` is required too.
- Fix is documented and cheap: add `llvm-config llvm-readobj llvm-objdump yaml2obj llvm-mc llvm-nm split-file`. Cost **3049 → 3130 edges = +81** measured on this tree today (an upstream filing prepared but **NOT YET FILED** §6); the project record (`CLAUDE.md`, and `WORKLIST.md`'s "Rebuilders' note" bullet) says **+82**. The one-edge difference is unexplained and nothing depends on it — recorded rather than reconciled silently.

### D34 — `stage/bin/` completed to 9 of 9 driver copies · **CLOSED** (2026-08-10)

> **CLOSED 2026-08-10.** REFUTED as still-missing. MEASURED this session: `ls -l stage/bin/` = **9**
> executables — `clang.exe`, `clang++.exe`, `clang-cl.exe`, `clang-cpp.exe`, `lld.exe`,
> `lld-link.exe`, and the three previously missing — **`ld.lld.exe`, `ld64.lld.exe`,
> `wasm-ld.exe`** — the latter three with mtime 2026-08-10 03:34. All nine run and all nine carry
> the shipped commit: `grep -ac 7653a13d8d28189c7cef1401b934ec30d98ea353` returns 2 on each.
> The project's working log's "9/9 driver copies" bullet records it independently: "9/9 driver copies staged (`ld.lld`, `ld64.lld`,
> `wasm-ld` added)." `stage/MODIFICATIONS.txt`'s shipped manifest ("bin/ 9 driver executables")
> only balances against 252 total files with 9, not 6. Closed by rt1's own packaging (PKG-1,
> `WORKLIST.md` T7) — the decision this row deferred was simply to add the three, and they were
> added. Everything below is the state of the row before this measurement, kept for the audit trail.

- The official package has exactly 9 byte-identical *separate copies* (link count 1 each, verified with two independent tools plus a purpose-built hardlink control): `clang.exe = clang-cl.exe = clang++.exe = clang-cpp.exe` and `lld.exe = lld-link.exe = ld.lld.exe = ld64.lld.exe = wasm-ld.exe`. `stage/bin/` had 6; missing `ld.lld.exe`, `ld64.lld.exe`, `wasm-ld.exe` (now present, see above).
- Only 2 are load-bearing (across three real build logs `clang-cl` appears 90/32/1 times and `lld-link` 363/388/376; the other seven appear **zero** times) — so the 9-file list is insurance, not necessity.
- Historical **WHY OPEN:** deliberately deferred — it was a packaging decision, `WORKLIST.md` **T7**, "record the options; decide in PKG-1, not here."

### D35 — MinGW ARM32 in the blast radius, untested · **OPEN**

- `ARMCOFFMCAsmInfoGNU` also sets `ExceptionsType = WinEH`, so `thumbv7-windows-gnu` takes the same `usesWindowsCFI()` path as MSVC. This makes **patch 0003** *and* **patch 0001** (whose trigger `ARMSubtarget::splitFramePointerPush` is gated on the same predicate) apply there.
- The scope statement is now recorded in the patch headers (T6): both ARM COFF asm infos named, and **rt1 validated on the MSVC target only**.
- **WHY OPEN:** MinGW ARM32 is **in-scope-by-construction, not tested** — a reader who takes the commit messages' "Windows ARM32" as MSVC-only would be wrong, and there is no measurement either way.
- **WHAT WOULD CLOSE IT:** run the 0001 and 0003 oracles once with `--target=thumbv7-windows-gnu` (both are compile-only host oracles, so this is cheap), with the stock compiler as the must-fail control — or state in the README that the GNU target is untested and unsupported.

### D36 — no upstream filing has been made · **OPEN**

- Working rule 12: filing upstream and fixing in rt1 are **ADDITIVE tracks, never alternatives**. Five of the six patched/known defects have a complete draft; **none has been filed** — filing is the USER's action (rule 11), and this project produces drafts in `upstream/` only.
- Drafts on disk `[measured]`: `ISSUE-bug5-backport.md` (D09, backport request, with the reduced IR appendix) · `ISSUE-bug1-musttail-forwarded-regs.md` (D01) · `ISSUE-bug2-lld-thumb-bit.md` (D04) · `COMMENT-bug4-issue-64278.md` (D07, a comment on an existing issue, not a new one) · `ISSUE-6-musttail-vararg-vastart.md` (D11) · `README-known-limitations.md`.
- Nothing to file for D05 (adjudicated WAI) or D12 (already fixed in released LLVM 21).
- **WHY OPEN:** the second track of rule 12 is untraversed for every row.
- **WHAT WOULD CLOSE IT:** the user files the five drafts and the issue numbers are recorded back into this table and into `CLAUDE.md`'s upstream ledger.

---

## Not defects — excluded from the table, with the reason (so nothing is silently dropped)

These appear in the reports as **owed work items**, not as defects, so they carry no defect verdict.
Their status is recorded here rather than being given a fabricated one.

| item | status |
|---|---|
| F4.3 — Bug-5 `llvm-reduce` IR reduction | **DONE** (the project's working log): 29,272,948 B → 1,492 B / 43 lines, verified both directions |
| F4.5 — upstream drafts for Bugs 1/2/4/#6 | **DONE** — files present; the *filing* is D36 |
| T5 — README known-limitations draft | **DONE** as a draft; §1 still carries `TBD-pending-Varan-grep`, which is D14 |
| T6 — doc wording (MinGW scope, P5 over-claim) | **DONE**; the underlying untested scope is D35 |
| C0 — commit hygiene | **CLEAN**, no correction needed |
| H4/H5/H6 — Varan relink, gates, device trip | ✅ **DONE 2026-08-09, ALL GREEN.** H4 rc=0 / 2,585 objects / 21 PEs (19 ours), both scaffolds removed · H5 all gates PASS exit 0 + 3 spot oracles · H6 staged 3,612 files, checksums verify, trip run on VENICE. **PKG-1 is UNBLOCKED** |
| Catalog §8 corrections owed to `CLANG-CL-THUMBV7-BUGS.md` | applied Varan-side on 2026-08-04 and the export was synced byte-identical (`RT-CLANG-FIX-1.md` §0 F0.1); re-sync obligation is H7 item 2 |

---

## Two things a reader of this table must not conclude

1. **"8 FIXED of 38" is not a coverage figure.** 12 rows are NOT-A-BUG and 1 is an OS hazard — those are
   *settled*, and 4 of the 8 FIXED rows are the catalog's four device-lethal/critical defects (the
   other 4 are the Bug-1 sub-instance D02, the non-critical diagnostic D12/#7, D11/#6, and D13's
   dump-crash — none device-lethal). 1 row is DISCLOSE outside the formal vocabulary (D14,
   pre-existing), 2 rows are ARMED — DEMONSTRATION OWED (D26, D27), and 1 is CLOSED (D34) — none of
   the three a defect verdict, see the vocabulary note above. The meaningful open surface is the
   **13 OPEN rows**, which partition exactly (re-derived 2026-08-10, after D11/D13 moved to FIXED,
   D26/D27 to ARMED, D34 to CLOSED, and D14 recognized as DISCLOSE rather than OPEN — it never was
   OPEN, it was miscounted into an earlier "19"): **1 compiler-defect recon in flight** (D15) ·
   **2 compiler-defect recon pending a patch decision** (D37, D38) · **2 pending a Varan-side
   measurement or decision** (D06, D10) · **3 instrument / gate / missing-oracle defects** (D25,
   D28, D29) · **5 packaging, scope or coverage** (D22, D31, D32, D35, D36). 1+2+2+3+5 = 13.
2. **No row here is a device claim.** Every measurement in this table is host-side. The device
   round-trip is H4–H6 and it has not run.
