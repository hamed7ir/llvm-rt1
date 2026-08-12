# D39 — family bound: **exactly ONE divergent type in the whole include set**

QUEUE item, run 2026-08-09. Compiler: `build/bin/clang-cl.exe` = `…18.1.8-rt1 (…7653a13d8…)`;
reference: MSVC 14.16 `cl.exe` for ARM (`19.16.27054`).

---

## RESULT

| type | clang align/size | MSVC align/size | |
|---|---|---|---|
| **`STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE`** (`winioctl.h:13430`) | 4 / **12** | 4 / **76** | ✗ **DIVERGE, 64 bytes** |
| `CLUSPROP_SECURITY_DESCRIPTOR` (`ClusApi.h:5180`) | 4 / **28** | 4 / **28** | ✓ **agree** |

Both derived from **wrapper member offsets** on both compilers, never from layout dumps.

**The family across the corpus's entire include set is TWO types, and only ONE diverges.**

---

## The trigger, and it is sharper than "FAM in a union"

The two candidates differ in exactly one respect:

```c
/* DIVERGES -- every member is a flexible array */
union {
    STORAGE_QUERY_DEPENDENT_VOLUME_LEV1_ENTRY Lev1Depends[];
    STORAGE_QUERY_DEPENDENT_VOLUME_LEV2_ENTRY Lev2Depends[];
} DUMMYUNIONNAME;

/* AGREES -- one member is a NORMAL object that dominates the union's size */
union {
    SECURITY_DESCRIPTOR_RELATIVE    sd;          /* <-- non-flexible */
    BYTE                            rgbSecurityDescriptor[];
} DUMMYUNIONNAME;
```

⇒ **The condition is a union whose members are ALL flexible arrays.** One non-flexible member is
enough for both compilers to agree, because that member sets the union's size.

### The arithmetic, MEASURED not assumed

Element sizes are **identical on both compilers** — so the element types are not the disagreement:

| | clang | MSVC |
|---|---|---|
| `…LEV1_ENTRY` | 32 | 32 |
| `…LEV2_ENTRY` | **68** | **68** |

The enclosing struct's header is two `DWORD`s = 8 bytes. Therefore:

* **MSVC 76 = 8 + 68** → MSVC reserves **one element of the largest union member**.
* **clang 12 = 8 + 4** → clang sizes the all-FAM union as effectively empty (1 byte, rounded to
  the union's alignment of 4).

> ⚠ **A wrong guess of mine, corrected by measuring.** I first reasoned "76 − 12 = 64, so MSVC
> reserves one 64-byte element". `LEV2_ENTRY` is **68**, not 64, so that arithmetic was wrong even
> though the conclusion direction was right. The correct decomposition is `8 + 68`, not
> `12 + 64`. Measuring the element sizes on *both* compilers is what settled it.

---

## Arming (queue item 2)

`famscan.py --self-test` — **PASS**:

| arm | result |
|---|---|
| POSITIVE | names the known member `_STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE`, and requires a hit in `winioctl.h` |
| NEGATIVE | a control fixture — a union of **non-flexible** arrays — is reported **not at all** |

⚠ **The arming earned its keep immediately.** The first version of the scan **failed its own
self-test**: it found the record but named it `DUMMYUNIONNAME`, because it read the first
`} NAME;` after the union — which is the *union's* close brace, not the enclosing struct's. Had
the self-test not demanded the known member **by name**, I would have reported a "bounded family"
whose only entries were named after a Microsoft macro.

---

## Upstream (queue item 3) — searched, and D39 may NOT be called unreported

**Search phrasings used, github.com only, 2026-08-09:**

1. `clang MSVC disagree sizeof struct flexible array member inside union zero-length array clang-cl ABI`
2. `clang-cl zero-sized array union sizeof differs MSVC unsized array member struct layout incompatibility`

**No direct hit.** Adjacent issues read, none of them this defect:

| issue | why it is NOT D39 |
|---|---|
| [#84565](https://github.com/llvm/llvm-project/issues/84565) — *"Allow C99 flexible array members in unions and alone in structs like 0-length arrays"* | **CLOSED**, implemented via PR #84428. It is about clang **ACCEPTING** the syntax, explicitly **not** about `sizeof` or MSVC size compatibility. Closest in construct, unrelated in symptom |
| [#95361](https://github.com/llvm/llvm-project/issues/95361) — clang-cl struct incompatible with MSVC ABI | **OPEN**, x64, `__m128`. Same *class* of complaint (clang-cl size ≠ MSVC size), different mechanism |
| [#136685](https://github.com/llvm/llvm-project/issues/136685) — `[[msvc::no_unique_address]]` layout differs from MSVC ABI | another MSVC-ABI layout divergence, different construct |

**Per standing caveat 3 this is "two searches failed", NOT "unreported."** Nothing about D39 may
be written up as a new/unreported finding on this basis alone.

---

## Outcome (queue item 5)

**Family bounded: 1 divergent type. Nothing live in the corpus** — the pass-1 sweep never laid the
record out, so no TU uses it; only the `-complete` sweep, which forces every declared record, sees
it at all.

⇒ **The release-note path applies, provisionally**: one *known differences* section covering
**D38a**, **D39**, and the all-FAM union case, under the agreed Bug-3 framing — *rt1 cannot prevent
this class; it makes it VISIBLE*.

**Provisionally**, because "nothing live" is answered for the rt1 corpus and **not** for the Varan
tree. That is a tree question and is handed off (queue item 4) as **H-D39** rather than answered
here. If a consumer does use an all-FAM union type, that consumer becomes the validation subject
and the row reopens as a patch candidate with the usual recon.

**Why this is not simply NOT-A-BUG:** the divergent type is an **IOCTL response struct**. A
64-byte size disagreement on a buffer handed to `DeviceIoControl` is a real hazard for any
consumer that allocates by `sizeof`. What makes it non-live here is that nothing uses it — not that
it would be harmless if something did.
