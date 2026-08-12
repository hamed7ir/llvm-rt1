# Patch 0007 — BINDING ACCEPTANCE SPEC (amendment V1–V4)

Written before the patch, deliberately. These are conditions the patch must MEET, not a list of
things to check afterwards and rationalise. Each one names its must-fail control, because a
condition that cannot fail has not been tested (working rule 3).

Source: user amendment "T8 verifier conditions + oracle hygiene", 2026-08-05. Recon and size
estimate: `scratch/T8/RECON-issue6.md` (verdict SMALL, ~200–240 patch lines).

---

## V1 — STACK: prove the arg-regs save area is deallocated before the tail branch

**Why this is the sharpest condition.** With the fix, a tail call and a **nonzero
`ArgRegsSaveSize`** coexist for the first time. The veto at `ARMISelLowering.cpp:3086-3091`
previously made that combination *impossible*, so the epilogue path that has to unwind that save
area before a `TCRETURN` is **untested by construction**. There is no existing regression coverage
to lean on, because the state was unreachable.

**Required evidence — not "the fatal is gone":**

1. Post-PEI MIR (`-stop-after=prologepilog`): the frame's `ArgRegsSaveSize` is nonzero, AND the
   SP adjustment before the tail branch accounts for it.
2. Disassembly: show SP at the branch equals the value the ABI requires — i.e. the incoming SP,
   with the save area released. Give the arithmetic explicitly (entry SP, each adjustment, final
   SP at `TCRETURN`/`bx`), the way `upstream/ISSUE-bug5-backport.md` does.
3. The `argRegsSaveSize` value must be shown, not assumed — read it out of the MIR.

**Must-fail control:** a deliberately wrong SP adjustment (or the same measurement taken on a build
without the epilogue fix, if the two are separable) must make the check FAIL. If no perturbation
can make this check fail, it is not a check.

**If the save area is NOT correctly released:** that is a real defect in 0007, not a caveat. STOP
and report; do not ship a patch whose only evidence is that the error message went away.

---

## V2 — SCOPE: prove the loosening is musttail-only

The recon's recommended scoping is musttail-only precisely so the blast radius is zero. That must
be **demonstrated**, not asserted.

**Required:** a lit test in which a **non-musttail** call in a `va_start` variadic function still
does **NOT** become a tail call, alongside the positive case where a musttail call now does.

**Must-fail control:** the negative directive must fail if the veto is loosened for non-musttail
calls. State plainly which CHECK directive discriminates — and per the T6 lesson on patch 0005, do
not describe pins as controls. Count the discriminating directives honestly.

---

## V3 — BYTE-IDENTICAL: measure it, and normalise the producer string first

**The trap, and it is the one that just bit the Bug-4 draft.** Adding patch 0007 changes the commit
hash, therefore the `Varan clang version 18.1.8-rt1 (<hash>)` producer string, therefore **every
object carrying DWARF or CodeView** — by a constant offset. That is the same **+188 B** mechanism
the Bug-4 reviewer caught. It must not be allowed to masquerade as a codegen change, and equally
must not be waved away as "just the version string" without being controlled for.

**Required:** compile a corpus with **rt1-before-0007** and **rt1-after-0007** and require
**identical objects**, having FIRST either
- disabled debug info entirely (no `-g`, no `-Zi`, no `-gcodeview`), or
- normalised the producer string out of the comparison,

and say which was done. Report the corpus size.

⚠ **SECOND TRAP — the COFF TimeDateStamp. Added 2026-08-05 from the T11 verifier, which hit it.**
Disabling debug info is **not sufficient**. A COFF object carries a `TimeDateStamp` at **offset 4**,
so two compiles of identical source differ in **bytes 5–8** unless they happen to land in the same
second. The T11 docs banked a "byte-identical, sha256 `4a8e3ac1…`" claim that reproduced only
because both compiles ran within one second; on re-run, `cmp` reported `differ: char 5` and `cmp -l`
showed exactly two differing bytes — the timestamp.

**Pass `-mno-incremental-linker-compatible`**, which zeroes it. MEASURED there: with the flag, rt1
and stock objects compiled 2 s apart hash identically
(`6884e189381982849268f69a9cee811e6fb3a79ce21420d0df3778e6bfc58cb6`), `cmp` clean.

**Triage rule:** if a byte-comparison fails, run `cmp -l` first. Differences confined to **offsets
4–7** are the timestamp, not codegen. Differences that are a *constant size delta* across every
object carrying debug info are the producer string. Neither is a codegen change, and both have
masqueraded as one in this project already.

**Must-fail control:** the comparison must be shown to detect a real difference — e.g. compare
against a build with a deliberate codegen change, or against pre-0001 output, and show it reporting
a difference. A byte-comparison that has never reported one is not armed.

**Identity arm (rule 13):** both compilers' `--version` must be captured and asserted to DIFFER
before the comparison runs. Use `tools/ab_arm.sh`.

---

## V4 — RUNTIME: the compile-succeeds oracle is NOT sufficient

**A successful compile proves the error is gone. It does not prove the code is right.** With a
forwarded `va_list`, wrong code compiles perfectly and reads garbage at runtime.

The T8.6 runtime `.exe` is therefore **MANDATORY**, and it must assert **`va_list` CONTENTS** — the
actual values read through the forwarded `va_list` — not merely that the program ran to completion.

**Required shape:**
- variadic musttail forwarder chains that call `va_start`, across several argument counts;
- mixed int/float arguments;
- an sret-returning shape;
- PASS/FAIL printed per case, **nonzero exit on any failure**;
- expected values derived by compiling and **RUNNING the identical source for x64 on the dev box** —
  the x64 run is the oracle, so the expected values are measured rather than hand-computed.

**Must-fail control:** perturb one expected value and confirm the harness reports FAIL and exits
nonzero. A self-checking test that has never failed is not known to check anything.

**Staged for the device trip** as `HANDOFF-TO-VARAN.md` item **H-VA** — that run is patch 0007's
acceptance evidence, and H-VA is written only once this `.exe` exists.

**THE EXE'S CONTENTS ARE THE ACCEPTANCE, NOT ITS EXIT CODE.** 0007 is the **only** patch in the
series with **no fleet consumer**: 0001–0006 each had the 19-PE build, the standing gates and a
device trip behind them. 0007 has lit, an A/B whose must-fail side is merely *a compiler error*, and
this one binary. So a thin executable means **0007 ships on inference**. It must read values back
through the forwarded `va_list` and compare them against x64-derived expectations, cover several
argument counts, mixed int/float, and the sret shape, and fail loudly **per case**.

---

## NOT SHIPPING 0007 IS A LEGITIMATE OUTCOME — authorised in advance

**If V1's stack arithmetic cannot be shown clean, do not ship the patch.** This is pre-authorised
(user, 2026-08-05), so that nobody has to weigh "completeness" against the evidence in the moment:

- The #6 disposition reverts to **file upstream with our analysis** — the recon in
  `scratch/T8/RECON-issue6.md` is a real contribution on its own: it identifies the exact veto
  (`ARMISelLowering.cpp:3086-3091`), proves the counter has two producers that collapse at
  `:4544-4545`, and shows the guard's own comment describes only the byval hazard.
- **Patches 0001–0006 are unaffected.** 0007 is additive and last in the series.
- Working rule 12 says fix every confirmed defect; it does **not** say ship a fix that could not be
  validated the way the rest were.

Completeness was the goal, but not at the price of the one patch that cannot be validated like the
others.

---

## Standing note on what 0007 CANNOT be validated by

There is **no fleet consumer**: Varan emits no `musttail` + `va_start` shape. So acceptance is lit
plus A/B plus the V4 runtime `.exe` — *not* a device-trip regression on shipped code. Working rule
12 says fix it anyway; rule 2 says the oracle must still be real. V4 is what makes it real.
