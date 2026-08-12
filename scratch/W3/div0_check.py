#!/usr/bin/env python
"""div0_check.py -- W3.2 / D15 acceptance gate for the compiler-rt builtins prototype.

WHAT IT DECIDES
    On thumbv7-*-windows-msvc, integer divide-by-zero must behave the way the PLATFORM
    behaves.  MEASURED (see the header block in D15-DIV0-DECISION.md): MSVC 14.16's
    `__rt_udiv` and `__rt_sdiv` (libcmt.lib, arm/divide.obj) both TRAP -- `__brkdiv0`,
    encoding 0xdef9 -- on a zero divisor.  compiler-rt's `arm/udivmodsi4.S` built without
    __ARM_EABI__ instead returns quotient 0 and NEVER WRITES the remainder out-parameter,
    so `__aeabi_uidivmod` reads an uninitialised stack slot.

    That second behaviour is not merely a divergence from MSVC.  It is undefined behaviour
    that rt1 would be INTRODUCING -- the one place in this project where we could ship a
    defect of our own rather than fix someone else's.  This gate exists so the prototype
    cannot be shipped without that being a deliberate, recorded decision.

THE PROPERTY CHECKED, and its stated limit
    PRIMARY  : the object must contain a divide-by-zero TRAP -- `__brkdiv0` (0xdef9), `udf`,
               or a reference to `__aeabi_idiv0`.
    SECONDARY: diagnostic only -- the count of stores through the remainder out-parameter
               register (r2) versus the count of return sites.  A return site with no
               preceding store on its path is how the uninitialised-slot read arises.

    LIMIT, STATED: the primary check proves a trap EXISTS in the object; it does not prove
    every divide-by-zero path reaches it.  A stronger check needs a CFG walk.  It is
    nevertheless decisive on the artifacts that exist today, which is what it is armed
    against below.

ARMED IN BOTH DIRECTIONS (working rule 3) -- `--self-test` runs both controls:
    POSITIVE control : MSVC 14.16 arm/divide.obj      MUST PASS  (the platform reference)
    MUST-FAIL control: rt1 prototype udivmodsi4.obj   MUST FAIL  (the defect under test)
    If either control does not produce its required verdict, the gate reports itself
    UNSOUND and exits 2 -- a gate that cannot fail is the standing defect class here.

USAGE
    python div0_check.py --self-test
    python div0_check.py <object-or-archive> [...]
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OBJDUMP = r"C:\Program Files\LLVM\bin\llvm-objdump.exe"
TRIPLE = "thumbv7-unknown-windows-msvc"

MSVC_REF = os.path.join(HERE, "divide.obj")                                # positive control
RT1_PROTO = os.path.join(HERE, "..", "T9b", "asm", "udivmodsi4.obj")       # must-fail control

# divide.obj is Microsoft's, extracted from libcmt.lib.  It is DELIBERATELY NOT COMMITTED --
# rt1 ships publicly and that object is not ours to redistribute.  Regenerate it on demand.
MSVC_LIB = (r"D:\Program Files\Vscom\VC\Tools\MSVC\14.16.27023\lib\arm\libcmt.lib")
LLVM_AR = r"C:\Program Files\LLVM\bin\llvm-ar.exe"


def ensure_msvc_ref():
    if os.path.exists(MSVC_REF) and os.path.getsize(MSVC_REF) > 0:
        return True
    if not os.path.exists(MSVC_LIB):
        print("  CANNOT RUN THE POSITIVE CONTROL: %s not found." % MSVC_LIB)
        print("  Without it the gate has no armed floor and its verdicts mean nothing.")
        return False
    subprocess.run([LLVM_AR, "x", MSVC_LIB, "--output=" + HERE, "divide.obj"],
                   capture_output=True, text=True)
    return os.path.exists(MSVC_REF) and os.path.getsize(MSVC_REF) > 0

TRAP = re.compile(r"\b(__brkdiv0|udf)\b|__aeabi_idiv0")
STORE_OUT = re.compile(r"\bstr(?:\.w)?\s+r\d+,\s*\[r2")
RETURN = re.compile(r"\bbx\s+lr\b|\bpop\s*\{[^}]*\bpc\b")


def disassemble(path):
    p = subprocess.run([OBJDUMP, "-d", "--triple=" + TRIPLE, path],
                       capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        raise SystemExit("objdump failed on %s:\n%s" % (path, p.stderr[:400]))
    return p.stdout


def check(path):
    """-> (verdict, traps, stores, returns)"""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise SystemExit("missing or empty: %s" % path)
    d = disassemble(path)
    traps = len(TRAP.findall(d))
    stores = len(STORE_OUT.findall(d))
    returns = len(RETURN.findall(d))
    return ("TRAPS" if traps else "NO-TRAP"), traps, stores, returns


def report(path):
    v, t, s, r = check(path)
    print("  %-9s trap-sites=%-3d  str-through-r2=%-3d  return-sites=%-3d  %s"
          % (v, t, s, r, os.path.basename(path)))
    return v


def self_test():
    print("div0_check.py --self-test   (triple %s)" % TRIPLE)
    print()
    if not ensure_msvc_ref():
        print("\nGATE UNSOUND -- positive control unavailable")
        return 2
    print("POSITIVE control -- MSVC 14.16 arm/divide.obj, the platform reference:")
    pos = report(MSVC_REF)
    print()
    print("MUST-FAIL control -- rt1 prototype compiler-rt arm/udivmodsi4.obj:")
    neg = report(RT1_PROTO)
    print()
    bad = []
    if pos != "TRAPS":
        bad.append("POSITIVE control did not trap -- the gate cannot recognise correct "
                   "platform behaviour, so a PASS from it would mean nothing")
    if neg != "NO-TRAP":
        bad.append("MUST-FAIL control passed -- the gate cannot detect the defect it "
                   "exists to detect (gate-vacuity)")
    for b in bad:
        print("  UNSOUND: %s" % b)
    if bad:
        print("\nGATE UNSOUND -- do not use its verdicts")
        return 2
    print("  GATE SOUND -- it recognises the platform reference and rejects the prototype.")
    print()
    print("  VERDICT ON THE PROTOTYPE AS IT STANDS TODAY: FAIL.")
    print("  It must not ship until its divide-by-zero path traps, or until a consumer")
    print("  records a deliberate decision to accept non-trapping semantics -- and even")
    print("  then the remainder out-parameter must be written, never left uninitialised.")
    return 1                       # non-zero: the prototype does NOT currently pass


def main():
    if "--self-test" in sys.argv or len(sys.argv) == 1:
        return self_test()
    worst = 0
    for a in sys.argv[1:]:
        if report(a) != "TRAPS":
            worst = 1
    return worst


sys.exit(main())
