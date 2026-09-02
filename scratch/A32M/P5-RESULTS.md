# p5 — SEH on ARM32 hardware. **Readings pre-registered 2026-09-02; trip returned the same day: PASS.**

This document is written **before** the device trip on purpose. Everything below the line marked
*RESULTS* is empty and stays empty until the kit comes back. The readings are fixed now so that no
outcome can be reinterpreted after it is seen.

## The question

*(Written before the trip, and left in the past tense it was written in.)* Patch 0009 gives rt1.1
Windows SEH for ARM32. **It compiled. It had never executed.** That was the same condition that
gated 0007, and it was the last thing standing between rt1.1 and a cut. **It has now executed —
see RESULTS.**

| arm | compiler | role |
|---|---|---|
| **A** | MSVC 14.16.27023 ARM32 | the **reference implementation** of Windows SEH on this target |
| **C** | rt1.1 — clang 18.1.8-rt1 @ `60876c5f8`, lld-link a73847036 | the port under test |

One source file (`scratch/A32M/p5.c`), both arms, ordinary Thumb frames only. The A32-frame oracle
is dead — trip-4 measured that **all three** toolchains, including clang `main`, fail to dispatch
across an unregistered dynamic frame — so this probe deliberately does not use one.

## PRE-REGISTERED READINGS

These are the only four conclusions this trip can produce. They are fixed in advance.

| outcome | reading |
|---|---|
| **all four modes match between arm A and arm C** | **rt1.1's SEH matches MSVC. Patch 0009 is ACCEPTED**, and the last gate before a cut is cleared. |
| **arm C differs from arm A on any mode** | **Attributable to our port** — MSVC is the reference implementation, so a divergence is ours, not the platform's. **That is the finding, and rt1.1 does not ship until it is explained.** |
| **control passes in either arm** | **VOID — the whole trip.** The probe cannot detect a dispatch failure, so no other mode is readable. `RUN.cmd` enforces this itself and stops without running the other modes. |
| **a mode crashes in BOTH arms** | **The platform, not our port.** MSVC failing the same way is the definition of not-our-bug. |

Note the asymmetry, and it is deliberate: a divergence blocks the release, a shared failure does not.

## The modes, and why `nested` is last

| order | mode | what it establishes |
|---|---|---|
| **1** | **`control`** | **MUST FAIL.** The filter returns `EXCEPTION_CONTINUE_SEARCH` and nothing else handles the fault, so the process **must die**. A non-zero exit is the correct result. If it survives, the instrument is blind and everything after it is meaningless. |
| 2 | `except` | the filter runs, sees the right exception code, and execution resumes after the `__except` block |
| 3 | `finally` | `__finally` runs on the **normal** path and again while **unwinding**, and the exception still reaches the outer `__except` |
| 4 | **`nested`** | the inner filter **declines** and the **outer** handler catches. This is the one that tells real stack unwinding apart from a single-frame shortcut, which is why it runs last. |

## What each mode must write

Per mode, per arm: **name · arm (A/C) · exit code · did the filter run · the exception code it saw ·
did execution resume where expected · `VERDICT=PASS\|FAIL\|VOID` with its reason.**

**No verdict is ever inferred from the absence of a crash.** The probe writes its own `VERDICT=` line
and flushes every record as it is written, so a hard crash preserves everything before it.

## The kit

`scratch/A32M/trip-p5/` — `RUN.cmd`, `bin\`, `MANIFEST.sha256`, `out\`, plus `README.txt` and
`PROVENANCE.txt`. Operator action: copy folder, run `RUN.cmd`, copy folder back. No transcription,
no hash checked by hand, no judgement call on the device.

`RUN.cmd` verifies both binaries with `certutil` against the manifest **before anything runs**, and
records device identity and code-integrity state — the device carries a modified SiPolicy, and a
measurement taken on such a device should say so rather than leave it to be assumed.

| file | sha256 |
|---|---|
| `bin\p5-A.exe` | `f1ecc3790d37b5ef2c713b5fa73804b5f339655c4e4feb1c3ef26af8ea0dca35` |
| `bin\p5-C.exe` | `18c12406a75c9aabdbef06ea9440188f4ff66f09d3d7fd630abffa314be39249` |

## The kit was proved to verify itself BEFORE it travels

Item 6. The kit was extracted to a clean directory outside the repo and its own `RUN.cmd` was run
there, on the x64 host. Both directions were exercised.

**Clean extraction — the hash check passes:**

```
[verify]
PASS p5-A.exe f1ecc3790d37b5ef2c713b5fa73804b5f339655c4e4feb1c3ef26af8ea0dca35
PASS p5-C.exe 18c12406a75c9aabdbef06ea9440188f4ff66f09d3d7fd630abffa314be39249
all binaries verified
```

**And the control-stop path fired end to end, unplanned.** The ARM32 probes cannot execute on an
x64 host, so neither produced an output file — which is exactly the condition the control logic
treats as "the must-fail arm did not die as required":

```
CONTROL_NO_OUTPUT_ARM=A
CONTROL_NO_OUTPUT_ARM=C
VERDICT=VOID_CONTROL_PASSED
```

**MEASURED: 0 entries for `except`, `finally` or `nested` in that log.** The script stopped where it
promised to, rather than reporting modes whose meaning the control had already destroyed. That is
item 3's rule demonstrated in the script, not merely asserted in the docs.

**Corrupted extraction — the hash check aborts:** a second copy with **one byte flipped** at offset
5000 of `p5-C.exe`:

```
PASS p5-A.exe f1ecc379...
FAIL p5-C.exe expected=18c12406a75c9aab... got=56918016bc4dbb2b...
VERDICT=ABORT_HASH_MISMATCH
```

with **0 probes run**. So the verification is armed in both directions: it passes a good kit and
stops a bad one before a single measurement is taken. A check that only ever prints PASS would
prove nothing.

The staged kit itself is pristine — 6 files, `out/` empty, both binaries re-verified against the
manifest. The tests ran in throwaway copies.

---

# RESULTS — trip returned 2026-09-02. **PASS. Reading 1 applies.**

> ## rt1.1's SEH matches MSVC, field for field, on real hardware. **Patch 0009 is ACCEPTED.**

Evidence banked verbatim at `scratch/A32M/results/trip-5-p5/` — nine files, byte-identical to what
came off the device.

## The device, on the record

```
COMPUTERNAME=DESKTOP-9C3DKH1
PROCESSOR_ARCHITECTURE=ARM
PROCESSOR_IDENTIFIER=ARM Family 7 Model C0F Revision 202, NVIDIA(R)     <- Tegra 3
NUMBER_OF_PROCESSORS=4
Microsoft Windows [Version 10.0.15035]
```

**Code integrity, recorded rather than assumed:** `nointegritychecks Yes`, `testsigning Yes`,
`flightsigning Yes`, with `SiPolicy.p7b` present. This device runs a modified code-integrity policy.
It does not affect what SEH dispatch does, but a measurement taken on such a device should say so.

## The kit verified itself before measuring anything

```
[verify]
PASS p5-A.exe f1ecc3790d37b5ef2c713b5fa73804b5f339655c4e4feb1c3ef26af8ea0dca35
PASS p5-C.exe 18c12406a75c9aabdbef06ea9440188f4ff66f09d3d7fd630abffa314be39249
all binaries verified
```

The binaries that ran are **exactly** the ones staged. That is the PF1 control doing its job.

## The must-fail control DIED — in both arms, first, before anything else

```
[p5 A control]  control.about_to_fault_with_no_handler=1   EXITCODE=-1073741819
[p5 C control]  control.about_to_fault_with_no_handler=1   EXITCODE=-1073741819
control died as required in BOTH arms - continuing
```

`-1073741819` is `0xC0000005`, `STATUS_ACCESS_VIOLATION`. Neither arm wrote `control.SURVIVED=1`.
**So the probe can detect a dispatch failure, and every result below is readable.** Had either
survived, `RUN.cmd` would have written `VERDICT=VOID_CONTROL_PASSED` and stopped.

## The three real modes: PASS in both arms

| mode | arm A (MSVC 14.16) | arm C (rt1.1) |
|---|---|---|
| `except` | **PASS**, exit 0 | **PASS**, exit 0 |
| `finally` | **PASS**, exit 0 | **PASS**, exit 0 |
| `nested` | **PASS**, exit 0 | **PASS**, exit 0 |

**And they are not merely both "PASS" — every recorded field is identical.** A `diff` of each mode's
output between the arms, excluding only the two lines that must differ, returns **nothing**:

```
except   filter_ran=1  filter_code=0xC0000005  filter_code_is_av=1  handler_body_ran=1
         code_in_handler=0xC0000005  code_agrees_filter_vs_handler=1  seq=5
         resumed_where_expected=1  stack_marker=0xA5A5F00D  stack_intact=1
finally  ran_on_normal_path=1  ran_on_exceptional_path=1  outer_filter_ran=1
         filter_code=0xC0000005
nested   inner_filter_ran=1  outer_filter_ran=1  outer_handler_ran=1
         filter_code=0xC0000005
```

`nested` is the one that matters most and it passed: **the inner filter declined and the OUTER
handler caught the exception**, which is real stack unwinding, not a single-frame shortcut.

## The arms really were two different builds — proved on the device

```
arm A   build_id=MSVC-14.16.27023-ARM-reference          built_by=MSVC _MSC_VER=1916
arm C   build_id=rt1.1-60876c5f8fad221756afd9bbd534377b7ff06571   built_by=clang 18.1.8
```

The identity arm held **on the hardware**, not only at staging. Two identical-looking PASS columns
produced by one compiler run twice would have been worthless; these carry their own provenance into
the results, which is exactly why `P5_BUILD_ID` was added.

## Verdict, against the readings fixed before the trip

Pre-registered reading **1**: *"all four modes match between arm A and arm C → rt1.1's SEH matches
MSVC and 0009 is accepted."* That is what happened, and no other reading is in play — the control
died (not reading 3), nothing diverged (not reading 2), and nothing crashed in both arms (not
reading 4).

**SEH has now executed on hardware.** The condition that gated 0007, and that was the last thing
standing between rt1.1 and a cut, is cleared.
