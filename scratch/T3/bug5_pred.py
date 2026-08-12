#!/usr/bin/env python3
"""
T3 --- SOUND interestingness predicate for Bug 5 (Windows ARM32 split R11/LR push,
       prologue over-allocates by GPRCS2/GPRCS3 size => same-object dual-base split).

REPLACES scratch/R6/split8.py, which is QUARANTINED: split8 worked on disassembly and
attributed references to frame objects by their *observed* address, so a base-pointer
reference that landed inside a neighbouring object's byte range was scored as a
divergence for that object.  That is a cross-product over (fp-refs x bp-refs), and it
false-positives on FIXED output.

THIS predicate never guesses attribution.  It joins on the INTENDED address, which is
exact arithmetic over the MIR frame-object table:

    pre-PEI  MIR  (-stop-before=prologepilog): frame indices are still symbolic
                  (%stack.K), so every reference's INTENDED entry-SP-relative address
                  is  frameobj[K].offset + immediate  -- by construction, not by search.
    post-PEI MIR  (-stop-after=prologepilog):  the same references carry real base
                  registers, so their ACTUAL address is  base_value + immediate, where
                  base values come from walking the emitted prologue.

    A frame object is a SAME-OBJECT DUAL-BASE carrier iff two references with intended
    addresses inside THAT ONE object's [offset, offset+size) byte range resolve to
    DIFFERENT actual addresses.

Memory references are joined between the two dumps by their machine-memory-operand name
(`:: (store (s32) into %ir.12)`), which PEI does not rewrite.  Address-formation
references (`$r0 = t2ADDri %stack.1, 0`, the address-of that escapes to a callee) carry
no MMO, so they are joined by a DERIVED-DEF ORDINAL: both sides count, in program order,
every definition of a register from an already-frame-derived register.  PEI rewrites one
such definition into several different opcodes (t2ADDri off the base pointer, t2SUBri off
the frame pointer, or a plain tMOVr), so the ordinal must count the EVENT, not the opcode.
The frame-pointer and base-pointer establishments are PEI-inserted and have no pre-PEI
counterpart, and are excluded from the count on both sides.

TWO THINGS THAT ARE EASY TO GET WRONG, both of which silently produce "no carriers":
  * Pre-PEI, every frame object reads `offset: 0` -- PEI is the pass that ASSIGNS offsets.
    The intended address must therefore use the POST-PEI frame table with the PRE-PEI
    immediates.  Reading offsets from the pre-PEI dump puts every object at 0.
  * The prologue walker must handle VSTMDDB_UPD (the VFP callee-save push) and the
    __chkstk static allocation, whose operand is a WORD count materialised into a register;
    and it must CONSUME that constant, because a VLA's t2SUBrr reuses the same register and
    would otherwise be counted as a second static allocation.

SOUNDNESS PROPERTY.  `over = prologue_total - stackSize` must be > 0, the two views of the
object must differ by exactly `over`, and the frame-pointer view must equal the declared
offset.  The predicate is therefore STRUCTURALLY INCAPABLE of firing on a compiler whose
prologue allocates the frame size PEI assigned -- which is the guarantee split8.py lacked.

exit 0 = INTERESTING (bug present)      exit 1 = not interesting      exit 2 = usage/parse
"""
import re, sys, collections

# ---------------------------------------------------------------- MIR parsing

FRAMEOBJ = re.compile(r"^\s*-\s*\{\s*id:\s*(\d+),.*?offset:\s*(-?\d+)"
                      r"(?:,\s*size:\s*(\d+))?", re.S)
STACKSZ  = re.compile(r"^\s*stackSize:\s*(\d+)")
FUNCNAME = re.compile(r"^name:\s+(\S+)")
MMO      = re.compile(r"::\s*\((?:volatile\s+)?(?:store|load)[^)]*\)\s*(?:into|from)?\s*(%ir[.\w]*|%stack\.\d+)")
MMO2     = re.compile(r"(?:into|from)\s+(%ir[.\w]+)")


def split_functions(text):
    """MIR files are a concatenation of YAML docs separated by '---'/'...'."""
    out, cur = [], []
    for line in text.splitlines():
        if line.startswith("---"):
            if cur:
                out.append("\n".join(cur))
            cur = []
        elif line.startswith("..."):
            if cur:
                out.append("\n".join(cur))
            cur = []
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return [f for f in out if FUNCNAME.search(f)]


def parse_header(fn):
    name = FUNCNAME.search(fn).group(1)
    ss = None
    m = re.search(STACKSZ.pattern, fn, re.M)
    if m:
        ss = int(m.group(1))
    objs = {}
    # frame objects are wrapped across two physical lines; rejoin on '- { id:'
    blob = fn
    for m in re.finditer(r"-\s*\{\s*id:\s*(\d+),(.*?)\}", blob, re.S):
        fid, body = int(m.group(1)), m.group(2)
        om = re.search(r"offset:\s*(-?\d+)", body)
        sm = re.search(r"size:\s*(\d+)", body)
        tm = re.search(r"type:\s*(\S+?),", body)
        if om is None:
            continue
        typ = tm.group(1) if tm else "default"
        objs[fid] = (int(om.group(1)), int(sm.group(1)) if sm else None, typ)
    return name, ss, objs


def body_lines(fn):
    m = re.search(r"^body:\s*\|\s*$", fn, re.M)
    if not m:
        return []
    return fn[m.end():].splitlines()


def mmo_name(line):
    m = MMO2.search(line)
    return m.group(1) if m else None


# ---------------------------------------------------------------- pre-PEI: INTENDED

def intended_refs(fn, objs_assigned):
    """-> (name, ss, objs, refs).  Each ref: dict(kind, key, intended).

    NOTE the frame-object table used here is `objs_assigned`, taken from the POST-PEI
    dump.  Pre-PEI every frame object still reads `offset: 0` -- PEI is the pass that
    assigns them.  The INTENDED address of a reference is therefore
    (PEI-assigned offset of the frame index it names) + (its pre-PEI immediate):
    the address PEI itself decided the object lives at, reached through the frame index
    the instruction actually named before rewriting.  The bug is that the emitted
    prologue does not put the object where PEI assigned it.
    """
    name, ss, _ = parse_header(fn)
    objs = objs_assigned
    sym = {}          # reg -> intended address of what it points at (entrySP-relative)
    refs = []
    ordinal = 0
    for line in body_lines(fn):
        s = line.strip()
        if not s or s.startswith(("bb.", "liveins", ";")):
            continue

        # base-register materialisation off a frame index
        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=\s*(?:nuw\s+|nsw\s+)?t2ADDri\s+%stack\.(\d+),\s*(-?\d+)", s)
        if m:
            reg, fi, imm = m.group(1), int(m.group(2)), int(m.group(3))
            if fi in objs:
                sym[reg] = objs[fi][0] + imm
                # a frame-derived register definition; see DERIVED-DEF ORDINAL below
                ordinal += 1
                refs.append(dict(kind="addr", key=("ord", ordinal),
                                 intended=objs[fi][0] + imm))
            continue

        # reg = t2ADDri/t2SUBri <reg-with-symbolic-value>, C   (virtual-base chaining)
        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=\s*(?:nuw\s+|nsw\s+)?t2(ADD|SUB)ri\s+(?:killed\s+)?(?:renamable\s+)?\$(\w+),\s*(-?\d+)", s)
        if m and m.group(3) in sym:
            sgn = 1 if m.group(2) == "ADD" else -1
            v = sym[m.group(3)] + sgn * int(m.group(4))
            sym[m.group(1)] = v
            ordinal += 1
            refs.append(dict(kind="addr", key=("ord", ordinal), intended=v))
            continue

        # plain copy propagates symbolic value
        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=\s*(?:COPY|tMOVr)\s+(?:killed\s+)?(?:renamable\s+)?\$(\w+)", s)
        if m:
            if m.group(2) in sym:
                sym[m.group(1)] = sym[m.group(2)]
                ordinal += 1
                refs.append(dict(kind="addr", key=("ord", ordinal),
                                 intended=sym[m.group(2)]))
            else:
                sym.pop(m.group(1), None)
            continue

        # memory op with a frame index directly as base
        m = re.search(r"\s%stack\.(\d+),\s*(-?\d+)", s)
        if m and ("STR" in s or "LDR" in s):
            fi, imm = int(m.group(1)), int(m.group(2))
            k = mmo_name(s)
            if fi in objs and k:
                refs.append(dict(kind="mem", key=("mmo", k),
                                 intended=objs[fi][0] + imm))
            continue

        # memory op through a symbolic base register
        if "STR" in s or "LDR" in s:
            m = re.search(r"(?:killed\s+)?(?:renamable\s+)?\$(\w+),\s*(-?\d+),", s)
            if m and m.group(1) in sym:
                k = mmo_name(s)
                if k:
                    refs.append(dict(kind="mem", key=("mmo", k),
                                     intended=sym[m.group(1)] + int(m.group(2))))
            continue

        # any other def kills the symbolic value
        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=", s)
        if m:
            sym.pop(m.group(1), None)
    return name, ss, objs, refs


# ---------------------------------------------------------------- post-PEI: ACTUAL

def actual_refs(fn):
    name, ss, objs = parse_header(fn)
    val = {}           # reg -> value relative to entry SP
    const = {}         # reg -> immediate, for the __chkstk word count
    cum = 0            # SP decrement so far
    frozen = False     # True once a DYNAMIC (VLA) allocation is reached
    nbb = 0
    refs = []
    ordinal = 0
    for line in body_lines(fn):
        s = line.strip()
        if not s or s.startswith(("liveins", ";")):
            continue
        if s.startswith("bb."):
            nbb += 1
            if nbb > 1:
                frozen = True        # only the entry block carries the prologue
            continue
        if "SEH_" in s or "ADJCALLSTACK" in s:
            continue

        # ---- prologue SP accounting -------------------------------------
        if "frame-setup" in s and not frozen:
            m = re.match(r"\$(\w+)\s*=\s*frame-setup\s+t2MOVi(?:16)?\s+(\d+)", s)
            if m:
                const[m.group(1)] = int(m.group(2))
                continue
            if "tPUSH" in s or "t2STMDB_UPD" in s:
                cum += 4 * len(re.findall(r"killed\s+\$(?:r\d+|lr)", s))
            elif "VSTMDDB_UPD" in s or "VSTMDBQIA_UPD" in s or "VSTMDIA_UPD" in s:
                cum += 8 * len(re.findall(r"\$d\d+", s))
            elif "t2SUBspImm" in s:
                cum += int(re.search(r"t2SUBspImm\s+killed\s+\$sp,\s*(\d+)", s).group(1))
            elif "tSUBspi" in s:
                cum += 4 * int(re.search(r"tSUBspi\s+\$sp,\s*(\d+)", s).group(1))
            elif "t2SUBrr" in s:
                # SP -= reg.  __chkstk with a materialised constant is a STATIC
                # allocation of (word count * 4); anything else is a VLA and ends
                # the static frame.
                mr = re.search(r"t2SUBrr\s+killed\s+\$sp,\s*(?:killed\s+)?\$(\w+)", s)
                if mr and mr.group(1) in const:
                    # consume it: __chkstk clobbers the operand register, so a later
                    # t2SUBrr on the same register is a different (dynamic) allocation
                    cum += 4 * const.pop(mr.group(1))
                else:
                    frozen = True

        # frame pointer / base pointer establishment.  Both are PEI-inserted and
        # have no pre-PEI counterpart, so neither may take a DERIVED-DEF ORDINAL.
        m = re.match(r"\$(\w+)\s*=\s*(?:frame-setup\s+)?tMOVr\s+(?:killed\s+)?\$sp\b", s)
        if m:
            val[m.group(1)] = -cum
            continue
        if "frame-setup" in s:
            continue

        # DERIVED-DEF ORDINAL --- must count exactly the same events as the pre-PEI
        # side, because address-formation references carry no memory operand and so
        # have no name to join on.  A "derived def" is a definition of a register
        # from an already-frame-derived register.  The frame-pointer establishment
        # ($rX = frame-setup tMOVr killed $sp) and the base-pointer establishment
        # ($rX = tMOVr $sp) are PEI-inserted and have no pre-PEI counterpart, so both
        # are excluded above before this point is reached.
        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=\s*(?:nuw\s+|nsw\s+)?t2(ADD|SUB)ri\s+(?:killed\s+)?(?:renamable\s+)?\$(\w+),\s*(-?\d+)", s)
        if m and m.group(3) in val:
            sgn = 1 if m.group(2) == "ADD" else -1
            v = val[m.group(3)] + sgn * int(m.group(4))
            val[m.group(1)] = v
            ordinal += 1
            refs.append(dict(kind="addr", key=("ord", ordinal), actual=v))
            continue

        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=\s*(?:COPY|tMOVr)\s+(?:killed\s+)?(?:renamable\s+)?\$(\w+)", s)
        if m:
            if m.group(2) in val:
                val[m.group(1)] = val[m.group(2)]
                ordinal += 1
                refs.append(dict(kind="addr", key=("ord", ordinal), actual=val[m.group(2)]))
            else:
                val.pop(m.group(1), None)
            continue

        if "STR" in s or "LDR" in s:
            m = re.search(r"(?:killed\s+)?(?:renamable\s+)?\$(\w+),\s*(-?\d+),", s)
            if m and m.group(1) in val:
                k = mmo_name(s)
                if k:
                    refs.append(dict(kind="mem", key=("mmo", k),
                                     actual=val[m.group(1)] + int(m.group(2))))
            continue

        m = re.match(r"(?:renamable\s+)?\$(\w+)\s*=", s)
        if m:
            val.pop(m.group(1), None)
    return name, ss, objs, refs, cum


# ---------------------------------------------------------------- verdict

def analyse(before_txt, after_txt, verbose=False):
    # post-PEI first: it carries the assigned frame-object offsets
    A = {}
    for fn in split_functions(after_txt):
        n, ss, objs, refs, total = actual_refs(fn)
        A[n] = (ss, objs, refs, total)
    carriers = []
    for fn in split_functions(before_txt):
        n0 = FUNCNAME.search(fn).group(1)
        if n0 not in A:
            continue
        ss, objs, refs, total = A[n0]
        if ss is None:
            continue
        n, _, _, brefs = intended_refs(fn, objs)

        over = total - ss
        if over <= 0:
            continue                       # clause 1: prologue must over-allocate

        # join intended <-> actual
        amap = {}
        for r in refs:
            amap.setdefault(r["key"], r["actual"])
        joined = []
        for r in brefs:
            if r["key"] in amap:
                joined.append((r["intended"], amap[r["key"]]))
        if not joined:
            continue

        # clause 2+3: SAME frame object, two different actual addresses
        for fid, (off, size, typ) in sorted(objs.items()):
            if size is None or typ == "spill-slot":
                continue
            inside = [(i, a) for (i, a) in joined if off <= i < off + size]
            if len(inside) < 2:
                continue
            acts = set()
            for i, a in inside:
                acts.add(a - (i - off))    # normalise to the object's base address
            if len(acts) < 2:
                continue
            delta = max(acts) - min(acts)
            if delta != over:
                continue                   # must be the prologue's own over-allocation
            # the FP view must be the CORRECT one (equal to the declared offset)
            if off not in acts:
                continue
            carriers.append(dict(fn=n, fi=fid, off=off, size=size,
                                 stackSize=ss, prologue=total, over=over,
                                 views=sorted(acts), refs=inside))
    return carriers


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    before = open(sys.argv[1], errors="replace").read()
    after = open(sys.argv[2], errors="replace").read()
    c = analyse(before, after)
    if c:
        for x in c:
            print("INTERESTING: same-object dual-base split")
            print("  function      : %s" % x["fn"])
            print("  frame object  : fi#%d  offset=%d size=%d" % (x["fi"], x["off"], x["size"]))
            print("  stackSize     : %d   prologue total: %d   over-allocation: +%d"
                  % (x["stackSize"], x["prologue"], x["over"]))
            print("  object seen at: %s   (declared %d)" % (x["views"], x["off"]))
        sys.exit(0)
    print("NOT-INTERESTING: no same-object dual-base split")
    sys.exit(1)


if __name__ == "__main__":
    main()
