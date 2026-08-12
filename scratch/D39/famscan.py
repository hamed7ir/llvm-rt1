#!/usr/bin/env python
"""famscan.py -- D39 step 1: enumerate SDK types with a FLEXIBLE ARRAY MEMBER inside a UNION.

The D39 mechanism, MEASURED 2026-08-09: an anonymous union whose only members are flexible
arrays (`T name[];`) is sized differently by clang and MSVC.  For
STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE the enclosing struct is clang 12 / MSVC 76 -- 64 bytes
apart.  This finds the rest of the family so the divergence can be BOUNDED rather than guessed
at.

Source-level scan of the corpus's own include set.  It is deliberately over-inclusive: every
candidate it names is then CONFIRMED by compiling a wrapper probe on both compilers
(famcmp.py), so a false positive here costs a compile, not a wrong answer.

ARMED (`--self-test`): the scan must find the KNOWN member -- winioctl.h's
_STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE -- and must stay silent on a control fixture with a
union of NON-flexible arrays.  A family sweep that has never named a known member is not
evidence.
"""
import os
import re
import sys

# a union block, then a flexible array member inside it: `TYPE name[];`
UNION_OPEN = re.compile(r"\bunion\b[^;{]*\{")
FAM = re.compile(r"^\s*[A-Za-z_][\w \t*]*\s+(\w+)\s*\[\s*\]\s*;")
# the enclosing named struct/typedef
TYPEDEF_END = re.compile(r"^\s*\}\s*([A-Za-z_]\w*)\s*,?")
STRUCT_OPEN = re.compile(r"^\s*typedef\s+struct\s+(\w+)|^\s*struct\s+(\w+)\s*\{")


def scan_text(text, path):
    """-> list of (enclosing_type, union_line, [fam_names])"""
    out = []
    lines = text.split("\n")
    enclosing, enc_line = None, 0
    depth_stack = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = STRUCT_OPEN.match(ln)
        if m:
            enclosing = m.group(1) or m.group(2)
            enc_line = i + 1
        if UNION_OPEN.search(ln):
            # collect until the matching close brace
            depth, j, fams = 0, i, []
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                if j > i or "{" in lines[j]:
                    fm = FAM.match(lines[j])
                    if fm:
                        fams.append(fm.group(1))
                if depth <= 0 and j > i:
                    break
                j += 1
            if fams:
                # NAME RESOLUTION -- the enclosing STRUCT is what a consumer can sizeof, and
                # it is what diverges.  An earlier version read the first `} NAME;` after the
                # union, which is the UNION's own close -- for the known member that yields
                # "DUMMYUNIONNAME" and the self-test correctly rejected it.  Prefer the
                # struct captured on the way in; fall back to a typedef close only if there
                # was none, and never accept a DUMMYUNIONNAME-style union member name.
                name = enclosing
                if not name:
                    for k in range(j, min(j + 12, len(lines))):
                        tm = TYPEDEF_END.match(lines[k])
                        if tm and tm.group(1).isupper() and "DUMMY" not in tm.group(1):
                            name = tm.group(1)
                            break
                out.append((name or "<anonymous>", path, i + 1, fams))
            i = j
        i += 1
    return out


def walk(roots):
    hits = []
    for root in roots:
        if not os.path.isdir(root):
            sys.stderr.write("famscan: missing include root: %s\n" % root)
            continue
        for dirpath, _, files in os.walk(root):
            for f in files:
                if not f.lower().endswith((".h", ".hpp")):
                    continue
                p = os.path.join(dirpath, f)
                try:
                    t = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                hits.extend(scan_text(t, p))
    return hits


_CTRL = """
typedef struct _CONTROL_OK {
    unsigned long A;
    union {
        unsigned long Fixed1[4];
        unsigned long Fixed2[8];
    } U;
} CONTROL_OK;
"""


def self_test(roots):
    fails = []
    hits = walk(roots)
    names = {h[0] for h in hits}
    if not any("STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE" in n for n in names):
        fails.append("POSITIVE: the KNOWN member "
                     "_STORAGE_QUERY_DEPENDENT_VOLUME_RESPONSE was NOT found")
    if not any("winioctl.h" in h[1].lower() for h in hits):
        fails.append("POSITIVE: winioctl.h produced no hit at all")
    ctrl = scan_text(_CTRL, "<control>")
    if ctrl:
        fails.append("NEGATIVE: control fixture (union of NON-flexible arrays) "
                     "was reported: %r" % (ctrl,))
    print("famscan.py --self-test")
    print("  candidates found      : %d" % len(hits))
    print("  known member present  : %s" %
          ("YES" if any("STORAGE_QUERY_DEPENDENT" in n for n in names) else "NO"))
    print("  control fixture quiet : %s" % ("YES" if not ctrl else "NO"))
    for f in fails:
        print("  FAIL: %s" % f)
    if fails:
        print("\nSELF-TEST FAILED -- this sweep's verdicts mean nothing")
        return 1
    print("  SELF-TEST PASSED -- names the known member, silent on the control")
    return 0


ROOTS = [
    r"D:\Windows Kits\10\Include\10.0.19041.0\um",
    r"D:\Windows Kits\10\Include\10.0.19041.0\shared",
    r"D:\Windows Kits\10\Include\10.0.19041.0\ucrt",
    r"D:\Windows Kits\10\Include\10.0.19041.0\winrt",
    r"D:\Program Files\Vscom\VC\Tools\MSVC\14.16.27023\include",
]


def main():
    if "--self-test" in sys.argv:
        return self_test(ROOTS)
    for name, path, line, fams in sorted(walk(ROOTS)):
        print("%s\t%s:%d\t%s" % (name, os.path.basename(path), line, ",".join(fams)))
    return 0


sys.exit(main())
