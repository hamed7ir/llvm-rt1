# W3.2 / D15 — divide-by-zero semantics: **DECIDED**

Session 2026-08-09. This closes the one item flagged as *"the place rt1 could ship a defect of
its own rather than fix someone else's"*. It is decided, not deferred.

---

## DECISION

> **The compiler-rt builtins prototype is BLOCKED from shipping in its current state.**
>
> Binding requirement, in priority order:
>
> 1. **The remainder out-parameter must never be read uninitialised.** This is unconditional.
>    It is undefined behaviour and it is *ours* the moment we ship the archive.
> 2. **On `thumbv7-*-windows-msvc`, integer divide-by-zero must TRAP**, matching the MSVC CRT's
>    `__brkdiv0`. Non-trapping semantics may be adopted only as a consumer's recorded,
>    deliberate decision — never as a default and never silently.
>
> Enforcement: `scratch/W3/div0_check.py`, armed in both directions. **It fails the prototype
> today**, by design, and will keep failing until (1) and (2) are satisfied.

---

## 1. What the platform actually does — MEASURED

The batch asked for the platform's behaviour rather than the specification's. It was read off
the shipping MSVC CRT, not inferred.

`llvm-ar x "…\14.16.27023\lib\arm\libcmt.lib" divide.obj`, then
`llvm-objdump -d --triple=thumbv7-unknown-windows-msvc divide.obj`:

```
00000000 <__rt_udiv>:
       0: b180         	cbz	r0, 0x24        <-- divisor == 0
       ...
00000024 <_lc001_002243_>:
      24: def9         	__brkdiv0           <-- TRAP
```

```
00000168 <__rt_sdiv>:
     ...
     178: b180         	cbz	r0, 0x19c       <-- same guard, signed path
```

`__brkdiv0` occurs **4 times** in `divide.obj`. Encoding `0xdef9` is `udf #0xf9`, the Windows
ARM32 divide-by-zero breakpoint.

**Platform behaviour: TRAP.** Not "return zero", not "return an unspecified value".

## 2. What the prototype does — MEASURED

rt1 tree, `compiler-rt/lib/builtins/arm/udivmodsi4.S:167-172`, the `#else` (non-`__ARM_EABI__`)
arm — which is the arm taken here, confirmed by `llvm-nm --undefined-only` on
`scratch/T9b/asm/udivmodsi4.obj` being **empty** (no `__aeabi_idiv0` reference):

```
LOCAL_LABEL(divby0):
	mov	r0, #0
	JMP(lr)          // no store through the remainder pointer
```

and the caller, `scratch/T9b/asm/aeabi_uidivmod.obj`:

```
       2: b081   sub  sp, #0x4     <-- slot allocated, never initialised on the div0 path
       4: 466a   mov  r2, sp
       6: bl     __udivmodsi4
       a: 9900   ldr  r1, [sp]     <-- reads it anyway
```

**New quantitative corroboration from this session's gate**, independent of reading the source:
`udivmodsi4.obj` has **3 stores through `r2` but 4 return sites** — exactly one return path that
never writes the remainder.

So: `x / 0` yields **quotient 0 and an indeterminate remainder read from an uninitialised stack
slot**. It neither traps nor zeroes.

## 3. Upstream's Windows accommodation does **not** fix this — READ-IN-SOURCE

Worth stating because it is the obvious place to look for a ready-made answer, and it is not
one. `compiler-rt/lib/builtins/arm/aeabi_uidivmod.S:18-20` and `:44-48`:

```asm
#if defined(__MINGW32__)
#define __aeabi_uidivmod __rt_udiv
#endif
...
#if defined(__MINGW32__)
        mov     r3, r0            // swap to the Windows (divisor, dividend) order
        mov     r0, r1
        mov     r1, r3
#endif
        bl      SYMBOL_NAME(__udivmodsi4)
```

It renames the symbol and swaps the argument order — but it still calls **compiler-rt's own**
`__udivmodsi4`, so the MinGW path carries **the identical divide-by-zero defect**. A function
called `__rt_udiv` that does not trap is arguably worse than one that does not pretend.

This also corrects a nuance in `scratch/D2/D2-compiler-rt-upstream.md`: the `__MINGW32__` block
is not *only* a rename, and its "exactly the wrong two symbols for Varan" objection applies to
the **rename** form. A **forwarding** form — keep `__aeabi_uidivmod` defined, tail-call the CRT
`__rt_udiv` — would preserve the two symbols Varan actually references
(`__aeabi_idivmod`, `__aeabi_uidivmod`, confirmed by the 607-object scan in D2 §4) *and* inherit
the platform's semantics by construction. That is the recommended shape if the archive is ever
completed; it is **not** implemented here, because D15's gate half remains **OURS/UNKNOWN**
pending the compiler-rt CMake files (D2 §1 names them).

## 4. Why this does not bite Varan today, and why that does not discharge it

Varan does not use this archive. Its shim tail-calls the CRT `__rt_*div`, which traps
(`aeabi-shim.c:27-30`, Varan tree, READ-ONLY reference), and SpiderMonkey zero-guards in
`divICommon`. So the live product is unaffected.

Under **working rule 12** that bounds severity and does not discharge the requirement. The
prototype is a release artifact for the community-RT consumer, who has neither the shim nor the
zero-guard.

## 5. The test

`scratch/W3/div0_check.py`. Armed in both directions on real artifacts:

```
POSITIVE control -- MSVC 14.16 arm/divide.obj, the platform reference:
  TRAPS     trap-sites=4    str-through-r2=0    return-sites=2    divide.obj

MUST-FAIL control -- rt1 prototype compiler-rt arm/udivmodsi4.obj:
  NO-TRAP   trap-sites=0    str-through-r2=3    return-sites=4    udivmodsi4.obj

  GATE SOUND -- it recognises the platform reference and rejects the prototype.
  VERDICT ON THE PROTOTYPE AS IT STANDS TODAY: FAIL.
```

Exit 1 — the non-zero is the point; it is the prototype failing, not the gate erroring. If
either control ever produces the wrong verdict the gate reports itself **UNSOUND** and exits 2
rather than passing anything.

**Stated limit** (in the script's own header too): the primary check proves a trap **exists** in
the object; it does not prove every divide-by-zero path reaches it. A stronger check needs a CFG
walk. It is decisive on the artifacts that exist today, which is what it is armed against.

## 6. Release-note wording

> On Windows ARM32, `x / 0` traps (`__brkdiv0`). Any compiler-rt builtins archive supplied for
> this target must preserve that. rt1 does **not** ship such an archive; the prototype in
> `scratch/` returns quotient 0 with an **indeterminate** remainder and is gated off by
> `scratch/W3/div0_check.py`.

Note the wording is *indeterminate*, not *zero* — the earlier "returns 0 silently" description
was right about the quotient and wrong about the remainder.
