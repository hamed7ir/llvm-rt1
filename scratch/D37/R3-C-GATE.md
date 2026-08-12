# R3 — acceptance gate for option **C** (backport BOTH D37 commits)

Specified 2026-08-09 so the post-trip run is **execution, not design**. Nothing here is run yet.

**C = backport `c1eb790cd2f2` + `82e64721974b` against 18.1.8.** Option A (drop, D37 stays a
documented limitation) remains the alternative and is the recorded outcome if any gate below fails.

---

## Prerequisite — the port recon must state the THREE-WAY INTERACTION, not just that each applies

`c1eb790cd2f2` is **+9 / −100 (net −91)** in `ARMISelLowering.cpp` (109 is the diffstat churn bar, not
a deletion count), and the function it guts —
`IsEligibleForTailCallOptimization` — is **already modified by two shipping rt1 patches**:

| patch | what it does to that function |
|---|---|
| **0003** (Bug 1) | adds the forwarded-must-tail register modelling; hunk 1 at `@@ -2474` in `LowerCall`, hunk 2 at `@@ -4679` in `LowerFormalArguments` |
| **0007** (defect #6) | rewrites the `getArgRegsSaveSize` / `getByValArgRegsSaveSize` veto **inside `IsEligibleForTailCallOptimization` itself** |
| **C's commit 1** | deletes the caller/callee argument-matching check **from the same function** |

**The recon is not complete until it answers, in writing and with line citations:**

1. Does `c1eb790cd2f2` delete or move any line that **0007 edits**? If yes, the two cannot both be
   applied verbatim and the merge must be authored, not resolved by `git apply`.
2. `c1eb790cd2f2` replaces the argument-matching check with *"the callee can't need more stack
   space for its arguments than the caller does"*. **Does that new condition subsume, contradict,
   or duplicate 0007's `getArgRegsSaveSize` veto?** Both concern the caller's incoming argument
   stack area. If upstream's new check makes 0007's veto dead code, say so — that is a finding
   about 0007, not only about C.
3. Does the deletion change behaviour for the shapes **0003** relies on (unprototyped
   perfect-forwarding thunks)? 0003's thunks are exactly the "arguments do not match" case that
   commit 1 relaxes.

**"All three apply cleanly" is NOT an answer to any of the above.** Apply-clean is a textual
property; these are semantic questions.

---

## GATE 1 (primary) — Varan fleet rebuild must be **BYTE-IDENTICAL**

**Rationale:** Varan emits **zero** `musttail`→`sret` call sites. If that is true, C cannot move a
single byte of the shipped product. So the strongest possible acceptance is available cheaply:
rebuild the fleet and diff.

| outcome | consequence |
|---|---|
| **Byte-identical to the trip-validated build** | The device trip's acceptance **carries over unchanged** — C is proven to have no effect on the product, and it ships on the strength of the trip that already happened. This is a far stronger result than any new test |
| **NOT byte-identical** | **STOP and report. The difference IS the finding** — it means either Varan does contain such a call site (and the trip validated a compiler that refused it), or C changes something beyond sret tail calls. Do not "investigate and continue"; stop |

**Measure it, do not assume it.** The claim "Varan emits zero musttail→sret" is the premise, not
the conclusion — and it is exactly the kind of premise this project has been wrong about before.

**Trap to avoid, already banked:** two benign metadata differences masquerade as codegen changes —
the COFF **TimeDateStamp** at offset 4 (build with `-mno-incremental-linker-compatible`) and the
**producer string** in debug info. Triage any diff with `cmp -l` before calling it a real change.

---

## GATE 2 — runtime acceptance, extended to the shapes that actually failed

Extend `scratch/D37/d37_runtime.cpp` (which already covers T/R/N and **passes on x64**) to make the
two failing shapes first-class:

| case | shape | why it is the point |
|---|---|---|
| **S** | `sret` + 6 × `i32` — two arguments on the stack | fatals on 0009-alone; commit 1's territory |
| **L** | `sret` + 5 × `i64` — four arguments on the stack | same, with 8-byte alignment in play |

Requirements, all three mandatory:

1. **Read the returned struct's FIELDS back**, per case, failing loudly and independently; exit
   code = number of failed cases.
2. **Expectations derived by RUNNING the same source on x64** — not hand-computed. Already done for
   T/R/N: x64 gives all-pass with guards intact.
3. **Armed floor: the control must FAIL on stock.** Stock 18.1.8 refuses to *compile* these shapes,
   which is a compile-time floor rather than a runtime one — state that explicitly, and add a
   spiked-expectations variant (the `VAFWD_EXPECTED_HEADER` pattern from
   `scratch/T8/V4/build-arm32.sh`) so there is a runtime floor too.

⚠ **`noinline` is load-bearing on every case** (working rule 14). Without it the callee is inlined
and no `musttail` reaches the backend, so the test passes while testing nothing. Say so in the
test.

---

## Already banked — do not re-derive (this is C's first half)

From the 0009 attempt, all still valid because they concern commit 2, which C also contains:

| check | result |
|---|---|
| armed floor | stock fatals, patched compiles |
| mismatched-sret still refused | **yes** — the change is bounded, not blanket |
| r0 (hidden sret pointer) written? | **never**, across all four shapes |
| SP net change at the branch | **0**, across all four shapes |
| branch form | plain `b.w` in every case, matching upstream's own CHECK |

---

## Failure disposition

If the recon cannot be stated cleanly, **or** GATE 1 is not byte-identical:

> **A-permanently.** D37 becomes a **documented known limitation** in the release notes — a loud
> compile-time refusal, never silent wrong code — plus an **upstream me-too citing both commits**
> and noting that 18.x/19.x never received either.
