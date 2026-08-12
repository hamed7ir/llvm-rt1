#!/usr/bin/env python
"""d38scan.py -- E2: find D38a CARRIERS in clang record-layout dumps.

THE INVARIANT IS INTERNAL, which is why this needs no reference implementation:

    a record whose  sizeof % alignof != 0  is a carrier BY DEFINITION.

That is a property of a single compiler's own output.  There is no MS-vs-Itanium
comparison here, so `tools/rt-layout-diff.py`'s structural blindness does not apply, and
no MSVC arm is needed.  (E1 separately established that MSVC gives 24 where clang gives
20 for the banked repro on ARM32 -- but that is the DIVERGENCE question, not this one.)

Input:  clang `-Xclang -fdump-record-layouts` output on stdin or in files.
Output: one line per carrier -- record name, sizeof, alignof, remainder.

ARMED FLOOR (working rule 3), `--self-test`:
  POSITIVE  the banked D38 repro's V1 (sizeof 20, align 8) MUST be reported.
  NEGATIVE  a control dump in which every record is well-formed MUST report zero.
  Both run on synthetic dumps, so the self-test needs no compiler.
A sweep that has never reported a carrier is not evidence of absence.
"""
import re
import sys

# clang emits:   |  [sizeof=20, align=8,          (MS)   or  nvsize=.., nvalign=..
SIZEOF = re.compile(r"\[sizeof=(\d+),\s*align=(\d+)")
# the record name is on the line that opens the dump: "         0 | struct Foo"
RECORD = re.compile(r"^\s*0 \| (?:struct|class|union) (.+?)\s*$")


def scan(text):
    """-> list of (record_name, sizeof, alignof)"""
    out, current = [], "<unknown>"
    for line in text.split("\n"):
        m = RECORD.match(line)
        if m:
            current = m.group(1)
            continue
        m = SIZEOF.search(line)
        if m:
            sz, al = int(m.group(1)), int(m.group(2))
            if al and sz % al:
                out.append((current, sz, al))
    return out


_POS = """*** Dumping AST Record Layout
         0 | struct I4
         0 |   int q
           | [sizeof=4, align=4,
           |  nvsize=4, nvalign=4]

*** Dumping AST Record Layout
         0 | struct V1
         0 |   (V1 vbtable pointer)
         8 |   double d
        16 |   struct I4 (virtual base)
        16 |     int q
           | [sizeof=20, align=8,
           |  nvsize=16, nvalign=8]
"""

_NEG = """*** Dumping AST Record Layout
         0 | struct Plain
         0 |   int a
           | [sizeof=4, align=4,
           |  nvsize=4, nvalign=4]

*** Dumping AST Record Layout
         0 | struct Wide
         0 |   double d
         8 |   char c
           | [sizeof=16, align=8,
           |  nvsize=16, nvalign=8]
"""


def self_test():
    fails = []
    pos = scan(_POS)
    if not any(n == "V1" and s == 20 and a == 8 for n, s, a in pos):
        fails.append("POSITIVE: the banked D38 repro (V1, sizeof 20, align 8) was NOT reported")
    if any(n == "I4" for n, _, _ in pos):
        fails.append("POSITIVE: well-formed I4 was wrongly reported as a carrier")
    neg = scan(_NEG)
    if neg:
        fails.append("NEGATIVE: control dump with no carriers reported %d" % len(neg))
    print("d38scan.py --self-test")
    print("  positive fixture -> %s" % (["%s %d/%d" % c for c in pos] or "NOTHING"))
    print("  negative fixture -> %s" % (["%s %d/%d" % c for c in neg] or "clean"))
    for f in fails:
        print("  FAIL: %s" % f)
    if fails:
        print("\nSELF-TEST FAILED -- the sweep's verdicts mean nothing")
        return 1
    print("  SELF-TEST PASSED -- the scanner reports a known carrier and stays silent on clean input")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    text = ""
    if args:
        for p in args:
            try:
                text += open(p, encoding="utf-8", errors="replace").read()
            except OSError as e:
                sys.stderr.write("d38scan: %s\n" % e)
    else:
        text = sys.stdin.read()
    hits = scan(text)
    for name, sz, al in hits:
        print("CARRIER\t%s\tsizeof=%d\talignof=%d\tremainder=%d" % (name, sz, al, sz % al))
    return 0


sys.exit(main())
