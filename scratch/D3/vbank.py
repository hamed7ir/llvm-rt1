# vbank.py -- D3 EXTENSION of scratch/FUZZ/bank.py: turn a diverging generated shape into a
# STANDALONE repro and re-confirm the divergence with the INDEPENDENT oracle (undefined
# template ShowSize<N> + __builtin_offsetof).  NO layout dump is involved, so a banked result
# cannot be a dump-format artifact.
#
# Why not bank.py itself: its blocks() splitter predates inheritance and has no notion of a
# type depending on another type, so the repro it writes for `struct S : B0, B1 {...}` omits
# B0/B1 and does not compile.  This version walks the dependency closure of the shape (leaves,
# bases, bases-of-bases) and emits exactly those, in declaration order.
#
# Rule 13: fuzz.arm_identity() runs before any compile and both arms are printed into the
# table, exactly as bank.py does.
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "FUZZ"))
import fuzz                                                       # noqa: E402

OUT = os.path.join(HERE, "repros")
NAME = re.compile(r"\b(L\d{3}_\d{2}|B\d{3}_\d{2}|S\d{6})\b")
DECL = re.compile(r"^(struct|union|class) (\w+)\b")


def split_tu(src):
    """-> (preamble, [(name, text)]) with #pragma push/pop lines attached to their record."""
    lines = src.split("\n")
    pre, blocks, i, n = [], [], 0, len(lines)
    while i < n:
        s = i
        while i < n and lines[i].startswith("#pragma"):
            i += 1
        if i >= n:
            pre.extend(lines[s:i])
            break
        m = DECL.match(lines[i])
        if not m:
            pre.extend(lines[s:i + 1])
            i += 1
            continue
        depth, j = 0, i
        while j < n:
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0 and "}" in lines[j]:
                break
            j += 1
        e = j
        while e + 1 < n and lines[e + 1].startswith("#pragma") and "pop" in lines[e + 1]:
            e += 1
        blocks.append((m.group(2), "\n".join(lines[s:e + 1])))
        i = e + 1
    return "\n".join(pre), blocks


def closure(target, blocks):
    by = dict(blocks)
    need, stack = set(), [target]
    while stack:
        t = stack.pop()
        if t in need or t not in by:
            continue
        need.add(t)
        for d in NAME.findall(by[t]):
            if d != t:
                stack.append(d)
    return need


# ----------------------------------------------------------------------------------------
# MEMBER PARSING.  Repaired 2026-08-09 (W3.1).
#
# THE DEFECT THIS REPLACES, and why it mattered:  the previous one-line matcher was
#     re.match(r"^\s+[\w:*]+(?:\s+[\w:*]+)* (\w+);$", ln)
# behind a blanket `if ":" in ln or ... : continue`.  Two whole member kinds could never
# match it and were dropped with NO diagnostic:
#   * ARRAY members  -- `L000_04 m1[3];`   the pattern demands `(\w+);` so `m1[3];` fails.
#   * ALIGN-ATTRIBUTED members -- `__declspec(align(1)) double m5;`  parentheses are not in
#     the `[\w:*]` class, so the whole line fails.
# MEASURED in the pilot corpus (scratch/D3/work, 8 TUs): 8 array members and 60
# align-attributed members present.  So this was ACTIVE under-reporting of probe coverage,
# not a latent hazard -- and `__declspec(align(1)) double m5;` is exactly the D14 shape, i.e.
# the harness was blind precisely where the open defect lives.
#
# THE REPAIR IS NOT ONLY A BETTER REGEX.  The defect class is "drops silently", so the fix
# has to be a reporting channel: every member-looking line that is not recognised is returned
# in `unparsed` and printed by main() as a loud UNPARSED line.  A future member kind we have
# not thought of therefore degrades to a visible gap instead of a silent one.
# ----------------------------------------------------------------------------------------

# an alignment specifier that may sit in front of the declaration
_ALIGN_PREFIX = re.compile(
    r"^(?:__declspec\s*\(\s*align\s*\(\s*\d+\s*\)\s*\)"
    r"|alignas\s*\(\s*\d+\s*\)"
    r"|__attribute__\s*\(\(\s*aligned\s*\(\s*\d+\s*\)\s*\)\))\s*")

# `<type words> name` optionally followed by array extents, then `;`
_MEMBER = re.compile(r"^(?P<type>[\w:*&]+(?:\s+[\w:*&]+)*?)\s+"
                     r"(?P<name>\w+)"
                     r"(?P<arr>(?:\s*\[\s*\d+\s*\])*)\s*;$")

_BITFIELD = re.compile(r":\s*\d+\s*;$")          # `int m : 3;`  and  `long long : 0;`
_STRUCTURAL = re.compile(r"^(?:\}|\};|\{|#pragma|//|$)")

# kept verbatim so the self-test can prove the new parser actually changed the outcome
_LEGACY = re.compile(r"^\s+[\w:*]+(?:\s+[\w:*]+)* (\w+);$")


def _legacy_own_plain(text):
    """The pre-2026-08-09 matcher.  Present ONLY as the self-test's must-fail arm."""
    out = []
    for ln in text.split("\n")[1:]:
        if ":" in ln or "{" in ln or "}" in ln or "virtual" in ln or "~" in ln:
            continue
        m = _LEGACY.match(ln)
        if m:
            out.append(m.group(1))
    return out


def _own_plain(text):
    """-> (names, unparsed).  `unparsed` is the whole point; see the block comment above."""
    out, unparsed = [], []
    for ln in text.split("\n")[1:]:
        s = ln.strip()
        if _STRUCTURAL.match(s):
            continue
        if "{" in s or "}" in s:                 # nested record, method body, record header
            continue
        if _BITFIELD.search(s):                  # STATED blind spot: offsetof cannot address
            continue                             # a bitfield.  Documented in probes().
        s = _ALIGN_PREFIX.sub("", s)             # strip an alignment specifier if present
        if "virtual" in s or "~" in s or "(" in s:
            continue                             # method / ctor / dtor, not a data member
        m = _MEMBER.match(s)
        if m:
            out.append(m.group("name"))
        else:
            unparsed.append(ln.strip())
    return out, unparsed


_NVBASES = re.compile(r"^(?:struct|class) \w+ : (.*?)\s*\{", re.S)


def probes(text, shape, by):
    """Members __builtin_offsetof can legally address: the shape's OWN plain members.

    -> (names, unparsed).  Array and align-attributed members ARE returned as of 2026-08-09;
    see the block comment above _ALIGN_PREFIX for what used to happen to them.

    TWO STATED BLIND SPOTS, both MEASURED this session rather than assumed:
      * BITFIELDS cannot be probed by __builtin_offsetof at all.  A shape whose only diverging
        members are bitfields therefore comes out UNCONFIRMED -- which is not the same as
        "agrees", and is reported as such.
      * Walking into non-virtual bases and probing THEIR plain members makes clang reject the
        probe once the most-derived class has a virtual base: 7 of 9 probes evaluated on the
        clang arm vs 9 on the MSVC arm for S000188.  The harness can only call that ORACLE
        INCOMPLETE, so the probe set stays inside the shape itself."""
    return _own_plain(text)


# ----------------------------------------------------------------------------------------
# ARMED SELF-TEST (working rule 3).  `python vbank.py --self-test` needs no compiler.
#
# It is armed in BOTH directions, which is the part that makes it worth having:
#   POSITIVE  the repaired parser must find the array member and the align-attributed member;
#   MUST-FAIL the LEGACY parser, kept verbatim above, must MISS both.  If someone reverts the
#             regex, `_own_plain` and `_legacy_own_plain` agree and the self-test FAILS.  A
#             self-test that only asserts the new behaviour would pass against the old code
#             the moment the two happened to coincide.
#   REPORTING an unrecognised member kind must land in `unparsed`, not vanish.
# ----------------------------------------------------------------------------------------
_FIXTURE = """struct SELFTEST {
    int plain;
    L000_04 arr[3];
    __declspec(align(1)) double aligned_below;
    __declspec(align(16)) long aligned_above;
    alignas(8) int alignas_form;
    unsigned long long bits : 43;
    long long : 0;
    void method(int);
    virtual void vmethod();
    ~SELFTEST();
    int trailing_garbage[;
};"""


def self_test():
    names, unparsed = _own_plain(_FIXTURE)
    legacy = _legacy_own_plain(_FIXTURE)
    fails = []

    want = ["plain", "arr", "aligned_below", "aligned_above", "alignas_form"]
    for w in want:
        if w not in names:
            fails.append("POSITIVE: repaired parser did not find member %r" % w)

    # bitfields and non-data members must NOT be probed
    for bad in ("bits", "method", "vmethod"):
        if bad in names:
            fails.append("POSITIVE: %r must not be probed (bitfield / non-data member)" % bad)

    # MUST-FAIL ARM: the legacy parser has to miss the two kinds this repair added back.
    for w in ("arr", "aligned_below", "aligned_above", "alignas_form"):
        if w in legacy:
            fails.append("MUST-FAIL ARM DID NOT FIRE: legacy parser already found %r -- the "
                         "self-test cannot tell the two parsers apart" % w)
    if set(legacy) == set(names):
        fails.append("MUST-FAIL ARM DID NOT FIRE: legacy and repaired parsers agree exactly; "
                     "the regex has probably been reverted")

    # REPORTING ARM: the malformed line must be visible, not silently dropped.
    if not any("trailing_garbage" in u for u in unparsed):
        fails.append("REPORTING: malformed member line was dropped silently instead of "
                     "being returned in `unparsed`")

    print("vbank.py --self-test")
    print("  repaired parser found : %s" % ", ".join(names))
    print("  legacy   parser found : %s" % ", ".join(legacy))
    print("  unparsed (reported)   : %s" % ", ".join(unparsed))
    print()
    if fails:
        for f in fails:
            print("  FAIL: %s" % f)
        print("\nSELF-TEST FAILED (%d)" % len(fails))
        return 1
    print("  SELF-TEST PASSED -- positive, must-fail and reporting arms all satisfied")
    return 0


def values(cmd, env=None):
    p = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True, env=env, errors="replace")
    return [int(x) for x in re.findall(r"ShowSize<(-?\d+)>", p.stdout + p.stderr)]


def build(tu, shape, seed):
    src = open(os.path.join(HERE, "work", "tu%04d.cpp" % tu)).read()
    pre, blocks = split_tu(src)
    by = dict(blocks)
    if shape not in by:
        raise SystemExit("%s not in tu%04d" % (shape, tu))
    need = closure(shape, blocks)
    sid = int(shape[1:])
    txt = ["// D3 LAYOUT-FUZZ-INHERITANCE banked repro -- STANDALONE, headerless.",
           "// corpus seed = %d   shape id (sid) = %d   TU = %d" % (seed, sid, tu),
           "// regenerate this shape with:  random.Random(%d * 1000003 + %d)" % (seed, sid),
           "// its TU's pools come from:    random.Random(%d * 7919 + %d)" % (seed, tu),
           "// Oracle is ShowSize<N> + __builtin_offsetof -- NO layout dump involved.",
           "// Only the dependency closure of %s is kept (%d of %d records)."
           % (shape, len(need), len(blocks)),
           "template <int N> struct ShowSize;", pre.strip()]
    for nm, t in blocks:
        if nm in need:
            txt.append(t)
    labels = ["__alignof(%s)" % shape, "sizeof(%s)" % shape]
    txt.append("ShowSize<__alignof(%s)> zz_align;" % shape)
    txt.append("ShowSize<sizeof(%s)> zz_size;" % shape)
    names, unparsed = probes(by[shape], shape, by)
    for p in names:
        txt.append("ShowSize<__builtin_offsetof(%s, %s)> zz_off_%s;" % (shape, p, p))
        labels.append("offsetof(%s)" % p)
    return "\n".join(txt) + "\n", labels, unparsed


def main():
    seed = 20260805
    if "--self-test" in sys.argv:
        return self_test()
    try:
        clang_id, msvc_id = fuzz.arm_identity()
    except fuzz.ArmError as e:
        sys.stderr.write("%s\nvbank.py: refusing to bank anything (working rule 13).\n" % e)
        return 3
    os.makedirs(OUT, exist_ok=True)
    print("identity arm (working rule 13), captured before any compile:")
    print("  clang arm : %s" % clang_id)
    print("  msvc  arm : %s" % msvc_id)
    print()
    env = fuzz.msvc_env()
    confirmed = 0
    todo = [a.split(":") for a in sys.argv[1:]]
    for tu, shape in todo:
        tu = int(tu)
        txt, labels, unparsed = build(tu, shape, seed)
        path = os.path.join(OUT, "repro_%s.cpp" % shape)
        open(path, "w").write(txt)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise SystemExit("failed to write %s" % path)
        vc = values([fuzz.RT1, "--target=thumbv7-unknown-windows-msvc", "-fsyntax-only", "-w",
                     "-fdeclspec", "-fms-extensions", path])
        vm = values([fuzz.MSVC, "-c", "-nologo", "-w", "-Fo" + shape + ".obj", path], env)
        print("== %s (tu%04d)  %s  [%d bytes, %d probes]"
              % (shape, tu, os.path.basename(path), os.path.getsize(path), len(labels)))
        for u in unparsed:
            print("   UNPARSED MEMBER (not probed, coverage gap): %s" % u)
        if len(vc) != len(labels) or len(vm) != len(labels):
            print("   ORACLE INCOMPLETE clang=%d msvc=%d expected=%d" % (len(vc), len(vm),
                                                                         len(labels)))
            continue
        diffs = [(l, a, b) for l, a, b in zip(labels, vc, vm) if a != b]
        if diffs:
            confirmed += 1
        for l, a, b in diffs:
            print("   %-34s clang=%-6d msvc=%-6d   DIVERGE" % (l, a, b))
        if not diffs:
            print("   (independent oracle: no difference on the probed quantities)")
    print()
    print("shapes banked: %d   confirmed diverging under the dump-free oracle: %d"
          % (len(todo), confirmed))
    print("repros in: %s" % OUT)
    print("arms: clang = %s" % clang_id)
    print("      msvc  = %s" % msvc_id)
    return 0


sys.exit(main())
