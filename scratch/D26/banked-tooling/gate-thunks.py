#!/usr/bin/env python3
# Varan (M3) -- STANDING GATE (R4-family) for the systemic
# virtual-PMF vcall-thunk fix. Runs every build alongside poison + dialect gate.
#
# A byte-scan for the broken pattern has false positives (the `ldr r1,[r0]; ...;
# bx r1` bytes occur coincidentally inside normal refcount/pointer code). This gate
# is EXACT and address-based: for EVERY linked binary that carries thunks it reads
# the thunk ADDRESSES from that binary's linker MAP (emitted by varan-ld-wrapper.sh
# as <binary>.goanna.map), then reads the first instruction at each ??_9<Class>@@$B
# <slot>@AA address and asserts it is the CORRECT `ldr.w r12,[r0]` (f8d0 c000), NOT
# the broken `ldr r1,[r0]` (6801). Any broken survivor => the override missed a thunk
# or was not applied to that binary => exit 1.
#
# Coverage: auto-discovers all *.goanna.map under the objdir, so it covers xul.dll,
# libGLESv2.dll, and any future thunk-carrying binary (not just xul).
#
# Usage: gate-thunks.py <objdir>
import sys, os, struct, re, glob

R1  = b"\x01\x68"          # ldr r1,[r0]      -> BROKEN
R12 = b"\xd0\xf8"          # ldr.w r12,[r0]   -> CORRECT (f8d0 -> bytes d0 f8)
THUNK_RE = re.compile(r"(\?\?_9\S*\$B[A-P0-9@]*)")
HEX_RE = re.compile(r"\b([0-9A-Fa-f]{8,16})\b")

def pe_map(binpath):
    data = open(binpath, "rb").read()
    pe = data.find(b"PE\0\0")
    magic = struct.unpack_from("<H", data, pe+24)[0]
    if magic == 0x20b:  # PE32+
        imgbase = struct.unpack_from("<Q", data, pe+24+24)[0]
    else:               # PE32
        imgbase = struct.unpack_from("<I", data, pe+24+28)[0]
    nsec = struct.unpack_from("<H", data, pe+6)[0]
    opt = struct.unpack_from("<H", data, pe+20)[0]
    sh = pe+24+opt
    secs = []
    for i in range(nsec):
        off = sh+i*40
        vs, va, rs, raw = struct.unpack_from("<IIII", data, off+8)
        secs.append((va, max(vs, rs), raw))
    return data, imgbase, secs

def va_to_off(secs, rva):
    for va, sz, raw in secs:
        if va <= rva < va+sz:
            return raw + (rva - va)
    return None

def gate_binary(binpath, mappath):
    data, imgbase, secs = pe_map(binpath)
    broken, correct, unresolved = [], 0, []
    for line in open(mappath, encoding="utf-8", errors="replace"):
        m = THUNK_RE.search(line)
        if not m:
            continue
        name = m.group(1)
        # the VA is the map's Rva+Base column: a hex token >= image base
        va = None
        for h in HEX_RE.findall(line):
            v = int(h, 16)
            if v >= imgbase:
                va = v; break
        if va is None:
            unresolved.append(name); continue
        off = va_to_off(secs, va - imgbase)
        if off is None:
            unresolved.append(name); continue
        b = data[off:off+2]
        if b == R1:
            broken.append((name, off))
        elif b == R12:
            correct += 1
        else:
            unresolved.append((name, b.hex()))
    return broken, correct, unresolved

def main():
    objdir = sys.argv[1] if len(sys.argv) > 1 else "."
    maps = glob.glob(os.path.join(objdir, "**", "*.goanna.map"), recursive=True)
    if not maps:
        print("GATE: no *.goanna.map found under %s -- override wrapper not active?" % objdir)
        sys.exit(1)
    # ★★ REPAIRED 2026-07-31 after review-4 agent A0 found three degenerate PASSes. ★★
    #  (1) `unresolved` was counted, printed, and then IGNORED. A thunk whose first
    #      instruction is neither the correct f8d0 nor the broken 6801 -- A0 used 0x4770
    #      (`bx lr`) -- was silently reclassified as `unresolved` and the gate PASSED.
    #      An unrecognised first instruction is an UNCHECKED thunk, not a good one.
    #  (2) A map with zero thunk lines, or a 0-byte map, printed
    #      "GATE PASS: all 0 vcall thunks" and exited 0. Zero is not a pass.
    #  (3) `any_thunks` was computed and NEVER USED -- the author clearly intended
    #      exactly this guard and it was never wired up.
    # Expected population on this tree (PDB census, A0-verified): 178 = xul.dll 176 +
    # libGLESv2.dll 2; the other 17 our-built PEs carry none. --expect-min lets the
    # caller assert a floor so a SHRINKING denominator is caught too; the tool cannot
    # know the right number itself, but the caller can.
    # ★ F0.2 (2026-08-04): the floor is now ARMED by both production callers --
    #   varan-interwork/run-suite.sh   and   varan-thunk-override/varan-fixup.sh,
    # each at --expect-min 178. Until today NO caller passed it, so the effective
    # floor was 1 and a count collapsing 178 -> 1 still printed GATE PASS
    # (gate-vacuity instance #11). Deliberately NOT armed in varan-interwork/
    # selftest.sh: its fixture is a xul-only temp copy = 176 thunks, so a 178 floor
    # there would make the clean-copy precondition SKIP the r12 proof, and would
    # make the expect-gate-FAIL control pass for the wrong reason.
    # The flag takes a SEPARATE value argument (`--expect-min 178`). The
    # `--expect-min=178` form used to be silently ignored, leaving the floor at 1 --
    # a flag that can be mistyped back into vacuity is not a gate, so that form and a
    # missing value are now hard errors rather than a silent downgrade.
    expect_min = 1
    for i, a in enumerate(sys.argv):
        if a.startswith("--expect-min=") or (a == "--expect-min" and i + 1 >= len(sys.argv)):
            print("GATE FAIL: --expect-min needs a separate value argument, e.g."
                  " `--expect-min 178`; got %r. Refusing to run with a floor that was\n"
                  "  parsed away silently." % a)
            sys.exit(2)
        if a == "--expect-min":
            expect_min = int(sys.argv[i + 1])
    total_broken = total_correct = total_unresolved = 0
    for mp in sorted(maps):
        binp = mp[:-len(".goanna.map")] + (".dll" if os.path.exists(mp[:-len(".goanna.map")]+".dll") else ".exe")
        if not os.path.exists(binp):
            continue
        broken, correct, unresolved = gate_binary(binp, mp)
        if correct or broken or unresolved:
            print("%-50s thunks: correct(r12)=%d broken(r1)=%d unresolved=%d"
                  % (os.path.basename(binp), correct, len(broken), len(unresolved)))
        total_broken += len(broken); total_correct += correct
        total_unresolved += len(unresolved)
        for name, off in broken[:20]:
            print("    BROKEN 0x%08x %s" % (off, name))
        for u in unresolved[:20]:
            print("    UNRESOLVED %s" % (u,))
    # The floor is printed so the LOG shows whether the caller actually armed it:
    # "floor=1" in a build log means that build's gate could not catch a collapse.
    print("\nthunks examined = %d  (correct=%d broken=%d unresolved=%d)  maps=%d  floor=%d"
          % (total_correct + total_broken + total_unresolved,
             total_correct, total_broken, total_unresolved, len(maps), expect_min))
    if total_broken:
        print("GATE FAIL: %d broken vcall thunk(s) survive across binaries." % total_broken)
        sys.exit(1)
    if total_unresolved:
        print("GATE FAIL: %d thunk(s) UNRESOLVED -- first instruction is neither the correct\n"
              "  f8d0 (ldr.w r12,[r0]) nor the known-broken 6801. These were NOT verified, and\n"
              "  'not verified' must never score as 'correct'." % total_unresolved)
        sys.exit(1)
    if total_correct < expect_min:
        print("GATE FAIL: only %d vcall thunk(s) found, expected at least %d. A collapsing\n"
              "  denominator means the map/relink stopped covering what it used to -- which is\n"
              "  indistinguishable from a pass unless it is checked." % (total_correct, expect_min))
        sys.exit(1)
    print("GATE PASS: all %d vcall thunks use r12 (arg1 preserved) across all binaries." % total_correct)
    class_census(objdir)


# =====================================================================================
# H1 (VARAN-ACCEPT-1, 2026-08-09) -- THE $4 / $R / ADJUSTOR CLASS EXTENSION
#
# WHY THE SECTION ABOVE IS NOT ENOUGH.  Bug 1 is not a property of the `??_9…$B…`
# mangling.  It is a property of ANY compiler-generated forwarding thunk whose
# parameters the ARM backend never modelled as live.  MSVC emits four such families --
# `$B` vcall, `$4` vtordisp, `$R` vtordispex, and the `G`/`O`/`W` adjustor thunks --
# and all four reach the musttail forwarder path.  The section above examines exactly
# one of them, in the two binaries that happen to have linker maps.
#
# ⚠ THE HANDOFF'S PROPOSED NAME REGEX WAS MEASURED AND IS NOT USABLE ALONE.
#   H1 step 1 asked for an anchored mangled-name regex `@@\$(?:R[024]|[024])`.
#   MEASURED over the 19 our-built ARMNT PEs of obj-browser-arm32-jit (189,713 distinct
#   exec names):
#       dbghelp "[thunk]:" marker ....... 6761 thunk names   ($B 178, $4 87, adj 6512)
#       the anchored regex .............. 3819 matches
#       overlap ......................... 72
#       thunks the regex MISSES ......... 6689  -- including $B 178/178 (100%) and
#                                                 adjustor 6511/6512
#       regex matches that are NOT thunks  3747  (false positives)
#   It misses the adjustor family because those mangle `@@W7…`/`@@O…`/`@@G…`, not
#   `@@$…`; and it misses `$B` ENTIRELY because the alternation `R[024]|[024]` does not
#   contain `B`.  Installing it as the classifier would have produced a gate blind to
#   the very class it was created for, while flagging 3747 innocent template names.
#   So classification is done by dbghelp's `[thunk]:` marker (FLEET-CENSUS.md §9 P2,
#   which independently rejected the `@$<digit>` regex for the same reason), and the
#   regex is kept only as a printed CONTROL so the disagreement stays visible.
#
# The engine is VENDORED, not reimplemented: varan-thunk-override/census/ is the same
# code that produced FLEET-CENSUS.md's numbers.  A reimplementation would be a new
# instrument with no measured provenance.  Verified on vendoring: it reproduces
# 4334 thunks / $B 44 / $4 73 / $R 0 / adj 4217 / 0 carriers / 0 IT-leak, exactly.
# =====================================================================================

CLASS_ORDER = ("$B", "$4", "$R", "adj", "thunk?")


def parse_class_floors(spec):
    """'B=44,4=73,R=0,adj=4217' -> {'$B':44,'$4':73,'$R':0,'adj':4217}"""
    out = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if not _:
            print("GATE FAIL: --class-floors entry %r has no '=' value." % part)
            sys.exit(2)
        key = k if k.startswith("$") or k == "adj" else "$" + k
        out[key] = int(v)
    return out


def class_census(objdir):
    """Census the adjustor thunk families and hold each class to its own floor.

    Silent no-op unless --class-floors is passed, so the existing callers keep working
    unchanged -- but see the WARNING it prints, because an unarmed class is precisely
    the vacuity this extension exists to remove.
    """
    spec = expect_pes = None
    for i, a in enumerate(sys.argv):
        if a.startswith("--class-floors=") or (a == "--class-floors" and i + 1 >= len(sys.argv)):
            print("GATE FAIL: --class-floors needs a separate value argument, e.g.\n"
                  "  `--class-floors B=44,4=73,R=0,adj=4217`; got %r. Refusing to run with\n"
                  "  a floor set that was parsed away silently." % a)
            sys.exit(2)
        if a == "--class-floors":
            spec = sys.argv[i + 1]
        if a == "--expect-pes":
            expect_pes = int(sys.argv[i + 1])

    if spec is None:
        print("\n[class census] NOT ARMED -- no --class-floors given, so the $4 / $R /\n"
              "  adjustor families were NOT examined. The $B result above covers ONE of the\n"
              "  FOUR thunk families MSVC emits. This is not a failure, but it is not\n"
              "  coverage either; arm it with e.g.\n"
              "    --class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19")
        return

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "census"))
    try:
        import engine
    except Exception as e:                                   # noqa: BLE001
        print("GATE FAIL: --class-floors was armed but the vendored census engine could\n"
              "  not be imported (%s). A gate that cannot run is NOT a pass." % e)
        sys.exit(1)

    floors = parse_class_floors(spec)
    pop = engine.build_population(objdir)
    print("\n[class census] population: %d our-built ARMNT PEs under %s/dist/bin"
          % (len(pop), objdir))
    if expect_pes is not None and len(pop) < expect_pes:
        print("GATE FAIL: only %d our-built ARMNT PEs found, expected at least %d.\n"
              "  A shrinking population is indistinguishable from a pass unless checked."
              % (len(pop), expect_pes))
        sys.exit(1)

    max_review = None
    for i, a in enumerate(sys.argv):
        if a == "--max-review":
            max_review = int(sys.argv[i + 1])

    KEYMAP = {"$B": "B", "$4": "v4", "$R": "vR", "adj": "adj", "thunk?": "other"}
    totals = dict.fromkeys(CLASS_ORDER, 0)
    carriers, other = [], dict.fromkeys(
        ("review", "beyond", "notfwd", "desync", "emptybody", "itleak"), 0)
    for rec in pop:
        r = engine.census_pe(rec)
        for k in CLASS_ORDER:
            totals[k] += r.get(KEYMAP[k], 0)
        for k in other:
            other[k] += r.get(k, 0)
        carriers += [row for row in r.get("rows", [])
                     if row.get("verdict") == "CARRIER"]

    examined = sum(totals.values())
    rc = 0

    # ---- INTEGRITY CONTROLS FIRST. These are the census's own self-checks, and if any
    # of them is non-zero the class counts below are MEANINGLESS -- so they are checked
    # before the counts are believed, not after.
    #   desync    a decoded region did not begin at its expected window offset
    #   emptybody a thunk address produced no instructions at all
    #   itleak    Thumb IT state leaked across a region boundary. This one FABRICATED a
    #             carrier before the 8-nop pad fixed it (FLEET-CENSUS pass-2 defect).
    for k in ("desync", "emptybody", "itleak"):
        if other[k]:
            print("GATE FAIL: census integrity control %s = %d (must be 0). The class\n"
                  "  counts below cannot be trusted and this run is VOID, not a pass."
                  % (k, other[k]))
            rc = 1
    print("\n  %-8s %-10s %-10s %s" % ("class", "found", "floor", "verdict"))
    for k in CLASS_ORDER:
        n = totals.get(k, 0)
        if k == "$R":
            # A floor of 0 is VACUOUS -- it can never fail. $R is asserted EXACTLY,
            # so any appearance at all is a finding rather than a silent pass.
            want = floors.get("$R", 0)
            ok = (n == want)
            print("  %-8s %-10d %-10s %s" % (k, n, "exactly %d" % want,
                                             "ok" if ok else "FAIL"))
            if not ok:
                rc = 1
        elif k in floors:
            ok = n >= floors[k]
            print("  %-8s %-10d %-10d %s" % (k, n, floors[k], "ok" if ok else "FAIL"))
            if not ok:
                rc = 1
        else:
            print("  %-8s %-10d %-10s %s" % (k, n, "-", "NOT ARMED (no floor)"))
            if n:
                rc = 1
    print("\n  thunk regions examined = %d across %d PEs" % (examined, len(pop)))
    print("  adjudication: carriers=%d review-framed=%d safe-beyond-window=%d not-forwarder=%d"
          % (len(carriers), other["review"], other["beyond"], other["notfwd"]))
    print("  integrity   : desync=%d emptybody=%d itleak=%d (all must be 0)"
          % (other["desync"], other["emptybody"], other["itleak"]))

    # `review-framed` means the model could not adjudicate the body. Per this gate's own
    # standing principle -- "not verified must never score as correct" -- that is held to
    # a caller-armed CEILING rather than waved through.
    if max_review is None:
        print("\n  [review-framed ceiling] NOT ARMED -- pass --max-review N to hold it.")
    elif other["review"] > max_review:
        print("\nGATE FAIL: %d review-framed thunk(s), ceiling is %d. These were NOT\n"
              "  adjudicated, and 'not adjudicated' must never score as 'safe'."
              % (other["review"], max_review))
        rc = 1

    if carriers:
        print("\nGATE FAIL: %d CARRIER(S) -- a forwarding thunk destroys an incoming\n"
              "  argument register that is inside the callee's live window." % len(carriers))
        for c in carriers[:20]:
            print("    CARRIER %s %s cls=%s clob=%s live=%s"
                  % (c.get("rel"), c.get("va"), c.get("cls"), c.get("clob"), c.get("live")))
            print("      sym: %s" % (c.get("names", [""])[0][:120],))
        print("  This is patch 0003's territory. Report before attempting any fix.")
        rc = 1
    if rc:
        sys.exit(1)
    print("\nGATE PASS: %d thunks across %d PEs, all four families examined, ZERO carriers."
          % (examined, len(pop)))


if __name__ == "__main__":
    main()
