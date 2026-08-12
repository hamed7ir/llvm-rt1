#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rt-layout-diff.py -- single-clang differential record-layout audit (MS ABI vs Itanium ABI).

WHY THIS EXISTS
---------------
One clang emits BOTH C++ record layouts; which one you get is selected by the TARGET TRIPLE
alone.  So a porter needs NO MSVC and no second toolchain to find the places where a struct
that was designed on Linux/GCC changes shape when it is rebuilt for Windows-on-ARM.

    --target=armv7-unknown-windows-msvc    ->  Microsoft record layout
    --target=armv7-unknown-linux-gnueabi   ->  Itanium record layout

*** SAME ARCHITECTURE ON BOTH SIDES.  THE ABI IS THE ONLY VARIABLE. ***
If you vary the architecture too, ordinary pointer-size / alignment differences masquerade as
ABI divergence and the output is garbage.  Both defaults above are armv7.  --ms-target and
--it-target let you move the pair, but keep the arch matched.

MEASURED (this tool's development session, rt1 clang D:\\repo\\llvm-rt\\build\\bin\\clang.exe):
across the default arch-matched pair the ONLY differing scalar is `wchar_t` (MS 2 bytes,
gnueabi 4 bytes).  sizeof/alignof of long, long long, double, long double, void*, bool are
identical on both sides.  `--short-wchar` adds -fshort-wchar to the Itanium side to remove
even that one confounder.

WHAT IT IS NOT
--------------
See the banner printed by every run: DIVERGENCE IS NOT A BUG.  This tool produces CANDIDATES.

REUSED BANKED MATERIAL (read before writing anything similar -- see CLAUDE.md working rules)
-------------------------------------------------------------------------------------------
  * D:\\repo\\llvm-rt\\scratch\\FUZZ\\layoutcmp.py   -- the strict clang-dump parser and the
    comparator.  IMPORTED, not re-implemented.  Its normalisation decisions D1..D4 (absolute
    bit offset as the key; unnamed bitfields; nested records; anonymous aggregates) are the
    reason this tool does not have its own half-parser.
  * D:\\repo\\llvm-rt\\scratch\\FUZZ\\repro_packdeclspec.cpp -- the `template <int N> struct
    ShowSize;` undefined-template trick: instantiate it with sizeof/alignof/offsetof and read
    the value straight out of the compiler's diagnostic.  No layout dump is involved, so it is
    a genuinely INDEPENDENT oracle.  --probe uses it, extended with a leading dummy tag type
    so each reported value self-identifies (ShowSize<RTLD_P7, 0, 12>) instead of having to be
    matched back by source column.
  * scratch/FUZZ/controls.py -- the C1 MUST-FIND / C2 MUST-FAIL control pattern that
    --self-test follows.

HARD CONSTRAINT
---------------
-Xclang -fdump-record-layouts-complete CRASHES the 18.1.8 base (177 of 185 TUs; RT1-WORKLOG.md
T1 pass 2).  This tool NEVER passes it.  Plain -fdump-record-layouts only lays out records that
are actually USED, so the tool generates a driver TU that forces each record complete via an
explicit template instantiation (works for abstract classes, classes with no default ctor,
classes with private members and unions -- all cases where "declare a variable of the type"
fails).

COMPILER IDENTITY (CLAUDE.md working rule 13)
---------------------------------------------
Every run captures `<clang> --version` before it compiles anything and prints that line in the
report header and in --self-test.  If the compiler was AUTO-DISCOVERED (no --clang), it must be
an rt1 build or the tool refuses with exit 2: the search order ends at PATH, where a stock
18.1.8 lives, and the old report showed only the path.  Pass --clang <path> to use any other
clang deliberately -- the differ itself needs no rt1 -- and the choice is recorded in the header.

EXIT CODES
----------
  0  no divergence found  (or --self-test passed)
  1  divergences found
  2  tool / compile / usage error  (including a failed identity arm)
  3  --self-test FAILED
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                      # D:\repo\llvm-rt

DEFAULT_MS_TARGET = "armv7-unknown-windows-msvc"
DEFAULT_IT_TARGET = "armv7-unknown-linux-gnueabi"


# --------------------------------------------------------------------------- banked parser

def load_layoutcmp(bankdir):
    """Import scratch/FUZZ/layoutcmp.py.  Loud failure, never a silent fallback parser."""
    cand = os.path.join(bankdir, "layoutcmp.py")
    if not os.path.isfile(cand):
        sys.stderr.write(
            "rt-layout-diff: FATAL: banked parser not found at %s\n"
            "  This tool deliberately does not carry a second copy of the dump parser.\n"
            "  Pass --layoutcmp-dir <dir containing layoutcmp.py>.\n" % cand)
        sys.exit(2)
    sys.path.insert(0, bankdir)
    import layoutcmp  # noqa: E402
    return layoutcmp


# --------------------------------------------------------------------- dump canonicalisation
#
# The banked parser is STRICT on purpose: an unrecognised line raises ParseError, because
# silent skipping is how a comparator starts reporting "equal" for everything.  Three dump
# line forms are emitted by clang for implicit/ABI-supplied slots that the banked parser was
# never shown (it was built for record shapes without inheritance).  Rather than loosening
# the parser, they are rewritten here into forms it already understands.  MEASURED line
# spellings, rt1 clang, this session:
#
#   MS   :  "         0 |   (ST_Poly vftable pointer)"      IT: "(ST_Poly vtable pointer)"
#   MS   :  "        12 |   (D vbtable pointer)"            IT: -- absent --
#   both :  "         0 |   struct B1 (primary base)"  /  "(base)" / "(virtual base)"
#   both :  "     4:0-2 |   int "                           (unnamed bitfield, trailing space)
#
# N1  vftable / vtable / vbtable pointers all become POSITIONAL "__abi_ptr#k" (k counted per
#     record per depth).  Rationale: naming them by kind would flag `struct X : virtual Y` as
#     divergent purely because MS puts a vbtable pointer at offset 0 where Itanium puts a
#     vtable pointer -- same offset, same sizeof, nothing a porter can break on.  Positional
#     naming keeps a genuinely EXTRA ABI pointer (MS vbptr on top of an inherited vfptr)
#     visible as a member-set divergence, which is real.
# N2  base subobjects become named aggregate members "__base_<T>" / "__vbase_<T>".  "(primary
#     base)" and "(base)" collapse to the same token: which base is primary is an ABI internal,
#     the OFFSET is what matters and is still compared.  Virtual bases keep a distinct token
#     because they are placed by a different rule.
# N3  unnamed bitfields get a positional name so their offsets are compared instead of being
#     dropped by the banked parser's D2 rule (D2 exists because MSVC's printer omits them --
#     irrelevant here, both sides are clang and print them identically).

_RE_VPTR = re.compile(r"^(?P<pre>.*\| )(?P<ind>\s*)\((?P<cls>.+?) v(?:f|b)?table pointer\)\s*$")
_RE_BASE = re.compile(r"^(?P<pre>.*\| )(?P<ind>\s*)(?P<kw>struct|class|union) (?P<ty>.+?) "
                      r"\((?P<kind>primary base|base|primary virtual base|virtual base)\)"
                      r"(?P<emp>(?: \(empty\))?)\s*$")
# N3 applies only to NON-zero-width unnamed bitfields.  The banked parser rejects a NAMED
# zero-width bitfield outright ("zero-width bitfield has a name"), and rightly: a zero-width
# bitfield occupies no storage, so it has no offset a porter can depend on.  Its effect lands
# in the following members and in sizeof/align, both of which are compared.
# (MEASURED: naming them broke on llvm-project/libunwind/include/unwind_arm_ehabi.h:64,
#  `long long int :0;` inside _Unwind_Control_Block.)
_RE_BFLINE = re.compile(r"^\s*\d+:\d+-\d+ \| ")
_RE_ANYLINE = re.compile(r"^(?P<pre>.*\| )(?P<ind>\s*)(?P<txt>.*)$")
_AGG_KW = ("struct ", "class ", "union ")

# N4  RECORD-HEADER LINE WITH NO struct/class/union KEYWORD.
#     The banked parser's _C_HDR is r"^\s*(\d+) \| (struct|union|class) (.*)$" -- the keyword
#     is mandatory.  clang prints the header as getTypeDeclType(RD).getAsString(), which for a
#     record that gets its name from a typedef of an ANONYMOUS tag prints the typedef name
#     ALONE.  MEASURED (rt1 clang, this session, hdrforms.cpp):
#         typedef struct { int a; } TD_S;        ->  "         0 | TD_S"
#         typedef union  { int a; } TD_U;        ->  "         0 | TD_U"
#         namespace ns { typedef struct {..} X;} ->  "         0 | ns::X"
#         struct Named { ... };                  ->  "         0 | struct Named"     (keyword)
#         struct { int a; } gAnon;               ->  "         0 | struct (unnamed at ...)"
#     `typedef struct {...} NAME;` is the dominant C idiom and is universal in the Windows SDK,
#     so ANY real porting input that reaches windows.h hits this.  Without N4 the STRICT parser
#     raises ParseError on the first such record and the whole run dies with exit 2 -- including
#     the records the user actually asked about, which had already parsed fine.
#     MEASURED before this rule existed: a 2-line input (`typedef struct { int a; char b; }
#     TDANON;` + a named control) -> "ParseError: bad record header '         0 | TDANON'",
#     exit 2, zero rows; and the same on a preprocessed js/src/jit/arm/Architecture-arm.h
#     ("bad record header '         0 | PPM_WMI_IDLE_STATE'", from winnt.h).
#     The rewrite inserts the keyword `struct` only.  The parser DISCARDS the keyword and keys
#     the record by the remaining text, so a union typedef is not mis-modelled: it is keyed by
#     its own name, identically on both sides, and struct-vs-union is not part of any
#     comparison.  Applied ONLY to the line immediately after the dump marker, so it can never
#     touch a member line.
_RE_HDRLINE_OK = re.compile(r"^\s*\d+ \| (?:struct|union|class) ")
_RE_HDRLINE_ANY = re.compile(r"^(?P<pre>\s*\d+ \| )(?P<rest>\S.*)$")


def _ident(s):
    return re.sub(r"[^0-9A-Za-z_]", "_", s)


def canonicalize_dump(text):
    """Rewrite ABI-specific dump spellings (N1/N2/N3/N4 above).  Returns new text."""
    out = []
    vptr_n = {}     # depth -> count, reset per record
    ubf_n = {}      # depth -> count, reset per record
    at_header = False
    for raw in text.split("\n"):
        ln = raw.rstrip("\r")
        if ln.strip() == "*** Dumping AST Record Layout":
            vptr_n = {}
            ubf_n = {}
            at_header = True
            out.append(ln)
            continue

        if at_header:                                                    # N4
            at_header = False
            if not _RE_HDRLINE_OK.match(ln):
                m = _RE_HDRLINE_ANY.match(ln)
                if m:
                    out.append("%sstruct %s" % (m.group("pre"), m.group("rest")))
                    continue
            out.append(ln)
            continue

        m = _RE_VPTR.match(ln)
        if m:                                                            # N1
            depth = len(m.group("ind")) // 2
            k = vptr_n.get(depth, 0)
            vptr_n[depth] = k + 1
            out.append("%s%svoid *__abi_ptr%d" % (m.group("pre"), m.group("ind"), k))
            continue

        m = _RE_BASE.match(ln)
        if m:                                                            # N2
            tok = "__vbase_" if "virtual" in m.group("kind") else "__base_"
            out.append("%s%s%s %s %s%s%s" % (m.group("pre"), m.group("ind"), m.group("kw"),
                                             m.group("ty"), tok, _ident(m.group("ty")),
                                             m.group("emp")))
            continue

        if _RE_BFLINE.match(ln):                                         # N3
            m = _RE_ANYLINE.match(ln)
            txt = m.group("txt")
            if txt.endswith(" ") and not txt.lstrip().startswith(_AGG_KW):
                depth = len(m.group("ind")) // 2
                k = ubf_n.get(depth, 0)
                ubf_n[depth] = k + 1
                out.append("%s%s%s__ubf_d%d_%d" % (m.group("pre"), m.group("ind"),
                                                   txt, depth, k))
                continue
        out.append(ln)
    return "\n".join(out)


# ------------------------------------------------------------------------------- process

def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def write_check(path, data, what):
    """Write an artifact and verify it EXISTS and is NON-EMPTY before anything parses it.
    (CLAUDE.md working rule 8 -- Windows path discipline.)"""
    with open(path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(data)
    if not os.path.isfile(path):
        raise ToolError("%s: expected artifact %s was not created" % (what, path))
    if os.path.getsize(path) == 0:
        raise ToolError("%s: artifact %s is EMPTY (0 bytes) -- refusing to parse it" %
                        (what, path))
    return path


class ToolError(Exception):
    pass


def find_clang(explicit):
    if explicit:
        if not os.path.isfile(explicit):
            raise ToolError("--clang %s does not exist" % explicit)
        return explicit
    for cand in (os.environ.get("RT_LAYOUT_DIFF_CLANG"),
                 os.path.join(REPO, "build", "bin", "clang.exe"),
                 os.path.join(REPO, "stage", "bin", "clang.exe")):
        if cand and os.path.isfile(cand):
            return cand
    w = shutil.which("clang") or shutil.which("clang.exe")
    if w:
        return w
    raise ToolError("no clang found; pass --clang <path to rt1 clang.exe>")


# ------------------------------------------------------------------- identity arm (rule 13)
#
# CLAUDE.md working rule 13.  This tool is SINGLE-COMPILER by construction: its two arms are
# TARGETS (--ms-target / --it-target) driven by ONE binary, so the assertion is the
# single-compiler form (`ab_arm_is <cc> --has rt1`), never the two-compiler form.
#
# WHAT GOES WRONG WITHOUT IT, specific to THIS tool: find_clang() picks a compiler by
# SEARCHING (RT_LAYOUT_DIFF_CLANG, then build/bin, then stage/bin, then PATH) and the report
# printed only the PATH it landed on -- never the compiler's identity.  MEASURED in this tree
# 2026-08-05:
#   * shutil.which("clang") resolves to C:\Program Files\LLVM\bin\clang.exe, which reports
#     "clang version 18.1.8" -- STOCK.  An absent or half-built build/ silently downgrades
#     every run to the unpatched compiler and nothing in the output says so.
#   * stage/bin/clang.exe reports 18.1.8-rt1 (...3afb49879...) while build/bin/clang.exe
#     reports 18.1.8-rt1 (...345ce564e...): a real ONE-PATCH-STALE rt1 sitting in the same
#     fallback chain, i.e. an rt1 without patch 0006.
# Neither is visible when only a path is printed, and this tool's own banner tells the reader
# the padding diagnostics "only fire on an rt1 clang carrying patch 0006".  So: capture the
# version line ONCE, PRINT it in the header and in --self-test (the commit hash inside it is
# what separates stale from fresh), and REFUSE an auto-discovered compiler that is not rt1.
# --clang is the deliberate-choice escape -- the differ itself works on any clang because it
# reads layout dumps -- and that choice is then RECORDED in the header instead of guessed.
#
# Runs ONCE per process, in main(), before any compile.  Unlike scratch/T3/interesting_rt1.sh,
# which runs once per llvm-reduce iteration and therefore caches its arm in a .armed sentinel,
# no caching is needed here.
#
# MIRRORED, NOT SHELLED OUT: tools/ab_arm.sh is bash, and this is a shipped consumer-facing
# tool that must not acquire a bash dependency on Windows.  clang_version_line() mirrors
# ab_arm_version() (tools/ab_arm.sh:25-35) and arm_identity() mirrors
# `ab_arm_is <exe> --has <needle>` (tools/ab_arm.sh:57-74): same first-line-of---version
# capture, same substring test, same refuse-loudly-and-abort contract.

ARM_NEEDLE = "rt1"


def clang_version_line(exe):
    """First line of `<exe> --version`.  Mirrors ab_arm_version() in tools/ab_arm.sh."""
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           errors="replace")
    except OSError as e:
        raise ToolError("could not run '%s --version': %s" % (exe, e))
    line = ((p.stdout or "").strip().split("\n") or [""])[0].strip()
    if not line:
        raise ToolError("'%s' produced no --version output; refusing to measure with a "
                        "compiler that cannot identify itself" % exe)
    return line


def arm_identity(exe, explicit):
    """Working rule 13, single-compiler form.  Returns the version line always; raises
    ToolError when an AUTO-DISCOVERED compiler is not the rt1 build."""
    v = clang_version_line(exe)
    if explicit:
        return v
    if ARM_NEEDLE not in v:
        raise ToolError(
            "IDENTITY ARM (CLAUDE.md working rule 13) -- REFUSING TO MEASURE.\n"
            "  auto-discovered clang : %s\n"
            "  it reports            : %s\n"
            "  required              : a version string containing '%s' (the rt1 build)\n"
            "  Until this check existed, the report printed only the PATH above, so a stock\n"
            "  18.1.8 picked up from PATH -- or a stale build/ -- was indistinguishable from\n"
            "  an rt1 result.  That is the Bug-4 near-miss, in this tool.\n"
            "  If you MEANT to use this compiler, say so explicitly:  --clang %s\n"
            "  The differ works on any clang (it reads layout dumps); an explicit choice is\n"
            "  printed in the report header instead of guessed."
            % (exe, v, ARM_NEEDLE, exe))
    return v


# --------------------------------------------------------------------------- driver TU

FORCE_TEMPLATE = (
    "template <class RTLD_T> struct RTLD_Force {\n"
    "  static const unsigned long long rtld_v = sizeof(RTLD_T) + __alignof(RTLD_T);\n"
    "};\n")

PROBE_TEMPLATE = (
    "// technique banked at scratch/FUZZ/repro_packdeclspec.cpp (ShowSize<N>), extended\n"
    "// with a dummy tag type so each reported value self-identifies.\n"
    "template <class RTLD_TAG, int RTLD_KIND, long long RTLD_N> struct ShowSize;\n")


def _preamble(include_path, block):
    """One python list element per PHYSICAL source line, so that a 1-based line number is
    exactly len(lines) after append.  (Bug found on real input: embedding the multi-line
    template as a single element desynchronised the line map from clang's diagnostics and
    made every blame lookup miss.)"""
    lines = ['#include "%s"' % include_path.replace("\\", "/"), ""]
    lines += block.rstrip("\n").split("\n")
    lines.append("")
    return lines


def make_force_driver(include_path, names):
    lines = _preamble(include_path, FORCE_TEMPLATE)
    linemap = {}
    for n in names:
        lines.append("template struct RTLD_Force< %s >;" % n)
        linemap[len(lines)] = n           # 1-based line number of that instantiation
    return "\n".join(lines) + "\n", linemap


def make_probe_driver(include_path, names):
    """kind 0 = sizeof, kind 1 = alignof.  Returns (source, idx -> (name, kind))."""
    lines = _preamble(include_path, PROBE_TEMPLATE)
    idx = {}
    i = 0
    for n in names:
        for kind, expr in ((0, "sizeof( %s )" % n), (1, "__alignof( %s )" % n)):
            lines.append("struct RTLD_P%d; ShowSize<RTLD_P%d, %d, %s> rtld_p%d;"
                         % (i, i, kind, expr, i))
            idx[i] = (n, kind)
            i += 1
    return "\n".join(lines) + "\n", idx


# ------------------------------------------------------------------------ record discovery

_RE_ENUMKW = re.compile(r"\benum\s+(?:class|struct)\b")
_RE_TAG = re.compile(r"\b(?:struct|class|union)\s+"
                     r"(?:__declspec\s*\([^()]*\)\s*)?"
                     r"([A-Za-z_]\w*)\s*"
                     r"(?:final\b\s*)?"
                     r"(?=[:{])")


_RE_LINEMARK = re.compile(r'^# (\d+) "(.*)"(.*)$')


def preflight(clang, target, include_path, extra, workdir, tag):
    """Prove the INPUT itself compiles for this triple before blaming anything on layout."""
    src = os.path.join(workdir, "preflight_%s.cpp" % tag)
    write_check(src, '#include "%s"\n' % include_path.replace("\\", "/"),
                "preflight TU (%s)" % tag)
    rc, out, err = run([clang, "--target=" + target, "-fsyntax-only", "-w",
                        "-ferror-limit=0"] + extra + [src])
    write_check(os.path.join(workdir, "preflight_%s.err.txt" % tag), err or "(clean)\n",
                "preflight diagnostics (%s)" % tag)
    if rc != 0:
        raise ToolError(
            "the INPUT does not compile for %s (rc=%d).\n"
            "  This is an input/environment problem, NOT a layout finding: both sides must\n"
            "  build before any comparison means anything.  Typical causes: the header pulls\n"
            "  in a C++ standard library that only exists for one of the two triples, or it\n"
            "  needs -I/-D.  Use -I/-D/--extra/--ms-extra/--it-extra, or -ffreestanding.\n"
            "  Full diagnostics: %s\n\n%s"
            % (target, rc, os.path.join(workdir, "preflight_%s.err.txt" % tag), err[:3000]))


def discover_records(clang, target, include_path, extra, workdir, tag):
    """Names of tag types DEFINED in NON-SYSTEM parts of the preprocessed translation unit.

    -E is used WITH line markers (not -E -P) so that the system-header flag `3` in
    `# <line> "<file>" 3` can be honoured.  Without that filter the scan harvests every tag
    in the CRT/STL that the input happens to pull in (MEASURED on a real header: it produced
    `__vcrt_va_list_is_reference` and friends).

    Still a heuristic, and advertised as one: it finds tag definitions at any scope but only
    by their UNQUALIFIED name, so members of namespaces / classes / templates are not
    nameable at global scope.  Those are pruned empirically by build_side()'s retry loop and
    the drops are REPORTED, never hidden.  Use --records to be exact.
    """
    src = os.path.join(workdir, "discover_%s.cpp" % tag)
    write_check(src, '#include "%s"\n' % include_path.replace("\\", "/"),
                "discover TU (%s)" % tag)
    rc, out, err = run([clang, "--target=" + target, "-E", "-w"] + extra + [src])
    if rc != 0:
        raise ToolError("preprocessing failed for %s (rc=%d)\n%s" % (target, rc, err[:4000]))
    write_check(os.path.join(workdir, "discover_%s.i" % tag), out, "preprocessed TU (%s)" % tag)
    user = []
    is_system = False
    for ln in out.split("\n"):
        m = _RE_LINEMARK.match(ln)
        if m:
            flags = m.group(3).split()
            if "3" in flags or "4" in flags:
                is_system = True
            elif "2" in flags or "1" in flags:
                is_system = False
            else:
                is_system = False
            continue
        if not is_system:
            user.append(ln)
    txt = _RE_ENUMKW.sub("enum", "\n".join(user))
    seen = []
    got = set()
    for m in _RE_TAG.finditer(txt):
        n = m.group(1)
        if n in got or n.startswith("RTLD_") or n == "ShowSize":
            continue
        got.add(n)
        seen.append(n)
    return seen


# -------------------------------------------------------------------------- one ABI side

class Side:
    def __init__(self, tag, target, records, dumped, dropped, dumpfile, ambiguous=()):
        self.tag = tag
        self.target = target
        self.records = records          # dict name -> layoutcmp.Record
        self.dumped = dumped            # raw canonicalised text
        self.dropped = dropped          # names that would not compile
        self.dumpfile = dumpfile
        self.ambiguous = list(ambiguous)  # printed names used by 2+ different records


# The banked parser POISONS a name printed by two different records (layoutcmp.py:210-214:
# `out[rname] = None` then the None entries are filtered out).  That is the right call --
# comparing "the first Foo" on one side against "the second Foo" on the other would be a
# fabricated result -- but the parser returns only the surviving dict, so from the tool's side
# the record simply CEASES TO EXIST: not compared, not asymmetric, not mentioned.
# MEASURED (this session, verifier repro dupname.cpp):
#     inline void f() { struct Dup { bool b:5; unsigned u:5; }; Dup x; (void)x; }   // divergent
#     inline void g() { struct Dup { unsigned a; };             Dup y; (void)y; }
#   -> "records compared: 0    divergent: 0 ... VERDICT: no divergence", EXIT 0
# i.e. a clean bill of health on a file whose only laid-out record IS divergent.  Local classes,
# anonymous-namespace types and same-named types in different headers all print identically, so
# this is reachable on ordinary input.  Recovering the layouts is not possible from the dump
# text (the printed name is all there is), so the fix is to make the drop VISIBLE.
def ambiguous_record_names(canon):
    """Names printed by 2+ distinct records in this dump -- the banked parser drops them."""
    counts = {}
    lines = canon.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() != "*** Dumping AST Record Layout" or i + 1 >= len(lines):
            continue
        m = re.match(r"^\s*\d+ \| (?:struct|union|class) (.*)$", lines[i + 1].rstrip("\r"))
        if not m:
            continue
        nm = m.group(1)
        if nm.endswith(" (empty)"):
            nm = nm[: -len(" (empty)")]
        nm = nm.strip()
        counts[nm] = counts.get(nm, 0) + 1
    return sorted(n for n, c in counts.items() if c > 1)


def build_side(lc, clang, tag, target, include_path, names, extra, workdir, no_instantiate,
               break_mode=None):
    """Compile one ABI side and parse its layouts.  Returns Side."""
    dropped = []
    # --no-instantiate hands the USER'S file straight to clang, so the language is inferred
    # from its EXTENSION.  A C++ header called .h is then compiled as a C HEADER while
    # preflight() has already compiled the same file as C++ inside a generated .cpp -- the
    # preflight passes and the measurement then dies on "unknown type name 'namespace'".
    # MEASURED (verifier repro lang.h, this session): a 2-line file
    #   `namespace N { struct S { bool b:5; unsigned u:5; }; }` + `N::S gv;`
    # gave "ERROR: layout dump failed for armv7-unknown-windows-msvc (rc=1) ... unknown type
    # name 'namespace'", exit 2.  Pin the language so the dump run and the preflight agree.
    lang = ["-xc++"] if no_instantiate else []
    if no_instantiate:
        src = include_path
        linemap = {}
    else:
        cur = list(names)
        src = os.path.join(workdir, "driver_%s.cpp" % tag)
        for _attempt in range(6):
            text, linemap = make_force_driver(include_path, cur)
            write_check(src, text, "driver TU (%s)" % tag)
            rc, out, err = run([clang, "--target=" + target, "-fsyntax-only", "-w",
                                "-ferror-limit=0"] + extra + [src])
            if rc == 0:
                break
            bad = set()
            for m in re.finditer(r"^.*?driver_%s\.cpp:(\d+):\d+: error:" % re.escape(tag),
                                 err, re.M):
                nm = linemap.get(int(m.group(1)))
                if nm:
                    bad.add(nm)
            if not bad:
                # preflight() already proved the input itself compiles, so an error that
                # cannot be blamed on any instantiation line is a real tool failure.  Loud.
                raise ToolError("driver TU for %s does not compile and no instantiation line "
                                "could be blamed. Driver kept at %s\n%s"
                                % (target, src, err[:4000]))
            dropped.extend(sorted(bad))
            cur = [n for n in cur if n not in bad]
            if not cur:
                raise ToolError("every candidate record was rejected by the compiler on %s"
                                % target)
        else:
            raise ToolError("driver TU for %s still failing after 6 pruning passes; last "
                            "driver kept at %s" % (target, src))

    rc, out, err = run([clang, "--target=" + target, "-fsyntax-only", "-w", "-ferror-limit=0",
                        "-Xclang", "-fdump-record-layouts"] + extra + lang + [src])
    if rc != 0:
        raise ToolError("layout dump failed for %s (rc=%d)\n%s" % (target, rc, err[:4000]))
    canon = canonicalize_dump(out)
    dumpfile = os.path.join(workdir, "dump_%s.txt" % tag)
    write_check(dumpfile, canon, "layout dump (%s)" % tag)
    if break_mode == "deaf":
        recs = {}
    else:
        recs = lc.parse_clang(canon, "%s/%s" % (tag, target))
    return Side(tag, target, recs, canon, sorted(set(dropped)), dumpfile,
                ambiguous_record_names(canon))


# ------------------------------------------------------------------------------ compare

class Divergence:
    def __init__(self, name, ms, it, kinds, first):
        self.name = name
        self.ms = ms
        self.it = it
        self.kinds = kinds          # list of (kind, detail)
        self.first = first          # (field, ms_bit, it_bit) | (field, ms_bit, None) | None


def first_divergent_field(ra, rb):
    """First field, in MS declaration order, whose absolute bit offset or width differs,
    or which is absent on the other side.  Returns (name, ms_bit, it_bit_or_None) or None."""
    mb = rb.bymap()
    ma = ra.bymap()
    for n in ra.order():
        if n not in mb:
            return (n, ma[n][0], None)
        if ma[n][0] != mb[n][0] or ma[n][1] != mb[n][1]:
            return (n, ma[n][0], mb[n][0])
    for n in rb.order():
        if n not in ma:
            return (n, None, mb[n][0])
    return None


def compare_sides(lc, ms, it, names, break_mode=None):
    """Returns (compared, [Divergence], missing)."""
    ncmp, div, missing = lc.compare(ms.records, it.records, names, "MS", "IT")
    if break_mode == "blind":
        div = []
    bykind = {}
    for nm, kind, detail in div:
        bykind.setdefault(nm, []).append((kind, detail))
    # layoutcmp.compare does not look at alignment; a record with equal sizeof but different
    # alignment is still a real layout divergence, so it is checked here.
    for nm in names:
        ra, rb = ms.records.get(nm), it.records.get(nm)
        if ra is None or rb is None:
            continue
        if ra.align is not None and rb.align is not None and ra.align != rb.align:
            if break_mode != "blind":
                bykind.setdefault(nm, []).append(
                    ("align", "MS=%d IT=%d" % (ra.align, rb.align)))
    if break_mode == "noisy":
        for nm in names:
            if nm in ms.records and nm in it.records:
                bykind.setdefault(nm, []).append(("BREAK-noisy", "injected"))
    out = []
    for nm in names:
        ra, rb = ms.records.get(nm), it.records.get(nm)
        if ra is None or rb is None or nm not in bykind:
            continue
        out.append(Divergence(nm, ra, rb, bykind[nm], first_divergent_field(ra, rb)))
    return ncmp, out, missing


# --------------------------------------------------------------------------- probe oracle

_RE_PROBE = re.compile(r"undefined template 'ShowSize<RTLD_P(\d+), (\d+), (-?\d+)>'")


def probe_side(clang, target, include_path, names, extra, workdir, tag):
    """Independent size/alignment oracle -- NO layout dump involved.
    Returns dict name -> (sizeof, alignof)."""
    src = os.path.join(workdir, "probe_%s.cpp" % tag)
    text, idx = make_probe_driver(include_path, names)
    write_check(src, text, "probe TU (%s)" % tag)
    rc, out, err = run([clang, "--target=" + target, "-fsyntax-only", "-w",
                        "-ferror-limit=0"] + extra + [src])
    write_check(os.path.join(workdir, "probe_%s.err.txt" % tag), err or "(no stderr)\n",
                "probe diagnostics (%s)" % tag)
    res = {}
    for m in _RE_PROBE.finditer(err):
        i, kind, val = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if i not in idx:
            continue
        nm, k = idx[i]
        cur = list(res.get(nm, (None, None)))
        cur[k] = val
        res[nm] = tuple(cur)
    return res


# ------------------------------------------------------------------------------- banner

BANNER = """\
================================================================================
rt-layout-diff -- single-clang MS-ABI vs Itanium-ABI record layout audit
================================================================================
*** DIVERGENCE IS NOT A BUG.  THIS TOOL REPORTS CANDIDATES, NOT DEFECTS. ***

  Both layouts are CORRECT for their ABI.  clang-cl implements the Microsoft rule
  faithfully; MSVC produces the same bytes.  A divergence only MATTERS where code
  actually depends on size or field offsets:
      - serialization / on-disk / on-wire formats
      - hand-written assembly reading fields by offset
      - casts or reinterpret_cast between two layouts of "the same" struct
      - memcpy / memcmp of whole structs across a boundary
      - static_assert(sizeof(X) == N) that was written on the Linux side
  Everything else is noise.  Do NOT send porters chasing it.

  rt1 WILL NEVER CHANGE RECORD LAYOUT.  Making clang-cl lay records out the Itanium
  way would desync from every MSVC-built ARM library, including the 14.16 CRT.  The
  supported fix is always in the SOURCE (e.g. give adjacent bitfields a uniform
  declared type, or use explicit masks) -- and that fix is PORTABLE: it produces the
  same layout under both ABIs.

NOTES
  - Most common trigger: adjacent bitfields with DIFFERING DECLARED TYPES.  Under the
    MS ABI each declared type starts a new allocation unit; under Itanium they pack.
    `bool` is incidental -- {unsigned short:5, unsigned:5} diverges exactly like
    {bool:5, unsigned:5}.  The rule is MS-ABI-wide, not an ARM32 defect.
  - -Wpadded / -Wpadded-bitfield are SILENT under Microsoft record layout on stock
    clang 18.  They only fire on an rt1 clang carrying patch 0006.  This tool does not
    need patch 0006 (it reads layout dumps), but that companion detector does.
  - -Xclang -fdump-record-layouts-complete is NEVER used: it crashes the 18.1.8 base.
    Records are forced complete by explicit template instantiation instead.
  - Known non-ABI confounder on the default pair: wchar_t is 2 bytes on the MS side and
    4 on gnueabi.  Pass --short-wchar to remove it.  (MEASURED: it is the ONLY differing
    scalar between armv7-*-windows-msvc and armv7-*-linux-gnueabi.)
  - Records present on only one side are reported as ASYMMETRIC, never dropped quietly.
    The usual cause is #ifdef _WIN32 / _MSC_VER inside the header.
================================================================================"""


def fmt_bit(b):
    if b is None:
        return "absent"
    return "byte %d bit %d (abs bit %d)" % (b // 8, b % 8, b)


def render(args, ms, it, ncmp, divs, missing, probes, allnames):
    w = sys.stdout.write
    w(BANNER + "\n")
    w("clang        : %s\n" % args._clang)
    w("clang version: %s%s\n" % (args._clang_version,
                                 "   [--clang given explicitly]" if args.clang else ""))
    w("MS  target   : %s\n" % ms.target)
    w("Itanium tgt  : %s\n" % it.target)
    w("input        : %s\n" % args._input)
    w("workdir      : %s\n" % args._workdir)
    w("dumps        : %s\n               %s\n" % (ms.dumpfile, it.dumpfile))
    w("records compared: %d    divergent: %d    asymmetric: %d\n"
      % (ncmp, len(divs), len(missing)))
    if ms.dropped or it.dropped:
        w("not nameable at global scope (skipped): MS=%s IT=%s\n"
          % (ms.dropped or "-", it.dropped or "-"))
    amb = sorted(set(ms.ambiguous) | set(it.ambiguous))
    if amb:
        w("AMBIGUOUS, NOT COMPARED (%d): one printed name, two or more different records --\n"
          "  the dump carries no way to tell them apart, so they are excluded rather than\n"
          "  guessed at.  Usual causes: local classes in different functions, types in an\n"
          "  anonymous namespace, same-named types in different headers.  Give them distinct\n"
          "  names, or audit them in separate runs.\n" % len(amb))
        for nm in amb[:40]:
            w("  %s\n" % nm)
        if len(amb) > 40:
            w("  ... and %d more (full dumps: %s , %s)\n"
              % (len(amb) - 40, ms.dumpfile, it.dumpfile))
    w("\n")

    # ONE table over every record that was compared, divergent rows first.  Listing the
    # records that came out IDENTICAL in the same table is deliberate: it is the run-time
    # evidence that "no divergence" is an outcome this instrument can actually produce.
    byname = {d.name: d for d in divs}
    ordered = [d.name for d in divs] + [n for n in allnames
                                        if n not in byname and n in ms.records
                                        and n in it.records]
    if args.divergent_only:
        ordered = [d.name for d in divs]
    # column width follows the data -- record names are never truncated into ambiguity
    nw = min(max([len("RECORD")] + [len(n) for n in ordered]), 84)
    w("RECORD LAYOUTS  (divergent first)\n")
    w("%-*s %-9s %-15s %-15s %s\n" % (nw, "RECORD", "STATUS", "MS size/align",
                                      "IT size/align", "FIRST DIVERGENT FIELD"))
    w("-" * (nw + 62) + "\n")
    if not ordered:
        w("(nothing to show)\n")
    for nm in ordered:
        ra, rb = ms.records.get(nm), it.records.get(nm)
        d = byname.get(nm)
        if d is None:
            w("%-*s %-9s %-15s %-15s %s\n"
              % (nw, nm, "identical", "%d/%s" % (ra.size, ra.align),
                 "%d/%s" % (rb.size, rb.align), "-"))
            continue
        first = "-- size/alignment only (tail padding) --"
        if d.first:
            fn, a, b = d.first
            first = "%s : MS %s | IT %s" % (fn, fmt_bit(a), fmt_bit(b))
        w("%-*s %-9s %-15s %-15s %s\n"
          % (nw, nm, "DIVERGENT", "%d/%s" % (d.ms.size, d.ms.align),
             "%d/%s" % (d.it.size, d.it.align), first))
        for kind, detail in d.kinds:
            w("%-*s   %s: %s\n" % (nw, "", kind, detail))
    w("\n")

    if missing:
        w("ASYMMETRIC RECORDS (laid out on one side only -- check #ifdef _WIN32/_MSC_VER)\n")
        for nm, a_missing, b_missing in missing:
            w("  %-38s missing on: %s\n" % (nm, "MS" if a_missing else "Itanium"))
        w("\n")

    if probes is not None:
        pms, pit, pnames = probes
        w("PROBE ORACLE (ShowSize<> undefined-template; no layout dump involved)\n")
        w("%-38s %-18s %-18s %s\n" % ("RECORD", "MS size/align", "IT size/align", "AGREES"))
        w("-" * 100 + "\n")
        # iterate the REQUESTED names, not just the ones that answered: a record the probe
        # could not measure (incomplete type, not nameable at global scope) is shown as
        # 'no value', never silently omitted.
        for nm in sorted(set(pnames) | set(pms) | set(pit)):
            a = pms.get(nm)
            b = pit.get(nm)
            if a is None and b is None:
                verdict = "no value (incomplete or not nameable)"
            else:
                verdict = "yes" if a == b else "NO"
            w("%-38s %-18s %-18s %s\n"
              % (nm[:38], "%s/%s" % a if a else "-", "%s/%s" % b if b else "-", verdict))
        w("\n")

    w("VERDICT: %s\n" % ("%d divergence candidate(s)" % len(divs) if divs
                         else "no divergence"))


# ------------------------------------------------------------------------------ self-test
#
# CLAUDE.md working rule 3: gates and screens need ARMED FLOORS.  A layout differ that cannot
# report a difference is worse than no differ at all, so --self-test must, IN ONE RUN, report
# BOTH a known-divergent shape AND a known-identical shape, with hardcoded expected sizes.
#
# Expected values MEASURED this session with rt1 clang D:\repo\llvm-rt\build\bin\clang.exe:
#   ST_DivBoolU32  MS 8 / IT 4   (0:0-4 then 4:0-4  vs  0:0-4 then 0:5-9)
#   ST_DivU16U32   MS 8 / IT 4
#   ST_SameU32     MS 4 / IT 4
#   ST_Plain       MS 16 / IT 16
#   ST_PlainNest   MS 24 / IT 24
#   ST_Poly        MS 8 / IT 8   (exercises the vftable/vtable canonicalisation)
#   ST_VBase       MS 24 / IT 24 (exercises vbtable-vs-vtable and the virtual-base line)

SELFTEST_SRC = """\
// rt-layout-diff self-test corpus.  Do not edit without re-measuring the table in the tool.
struct ST_DivBoolU32 { bool b : 5;           unsigned u : 5; };  // MS 8 / IT 4  DIVERGENT
struct ST_DivU16U32  { unsigned short a : 5; unsigned u : 5; };  // MS 8 / IT 4  DIVERGENT
struct ST_SameU32    { unsigned a : 5;       unsigned u : 5; };  // 4  / 4       IDENTICAL
struct ST_Plain      { char c; int i; double d; };               // 16 / 16      IDENTICAL
struct ST_PlainNest  { ST_Plain p; char t; };                    // 24 / 24      IDENTICAL
struct ST_Poly       { virtual ~ST_Poly(); int x; };             // 8  / 8       IDENTICAL
struct ST_VBase : virtual ST_Plain { int d; };                   // 24 / 24      IDENTICAL
"""

SELFTEST_NAMES = ["ST_DivBoolU32", "ST_DivU16U32", "ST_SameU32", "ST_Plain",
                  "ST_PlainNest", "ST_Poly", "ST_VBase"]
SELFTEST_EXPECT_DIVERGENT = {"ST_DivBoolU32", "ST_DivU16U32"}
SELFTEST_SIZES = {                        # (MS sizeof, IT sizeof)
    "ST_DivBoolU32": (8, 4), "ST_DivU16U32": (8, 4), "ST_SameU32": (4, 4),
    "ST_Plain": (16, 16), "ST_PlainNest": (24, 24), "ST_Poly": (8, 8),
    "ST_VBase": (24, 24)}
# teeth beyond "it was flagged": the offending member and its exact bit offsets.
SELFTEST_FIRST = {"ST_DivBoolU32": ("u", 32, 5), "ST_DivU16U32": ("u", 32, 5)}


def self_test(args, lc):
    w = sys.stdout.write
    fails = []
    workdir = args._workdir
    src = os.path.join(workdir, "selftest_corpus.h")
    write_check(src, SELFTEST_SRC, "self-test corpus")

    it_target = args.it_target
    if args.self_test_break == "vacuous-target":
        it_target = args.ms_target        # <- the classic gate-vacuity injection

    w(BANNER + "\n")
    w("SELF-TEST\n")
    w("clang       : %s\n" % args._clang)
    w("clang ver   : %s%s\n" % (args._clang_version,
                                "   [--clang given explicitly]" if args.clang else ""))
    w("MS  target  : %s\n" % args.ms_target)
    w("IT  target  : %s\n" % it_target)
    w("break mode  : %s\n" % (args.self_test_break or "none (normal run)"))
    w("corpus      : %s\n\n" % src)

    bm = args.self_test_break
    ms = build_side(lc, args._clang, "ms", args.ms_target, src, SELFTEST_NAMES,
                    args._ms_extra, workdir, False, bm)
    it = build_side(lc, args._clang, "it", it_target, src, SELFTEST_NAMES,
                    args._it_extra, workdir, False, bm)
    ncmp, divs, missing = compare_sides(lc, ms, it, SELFTEST_NAMES, bm)
    divnames = set(d.name for d in divs)
    byname = {d.name: d for d in divs}

    w("%-16s %-10s %-10s %-12s %-12s %s\n"
      % ("RECORD", "MS size", "IT size", "expected", "verdict", "detail"))
    w("-" * 104 + "\n")
    for nm in SELFTEST_NAMES:
        mine = []                       # failures attributable to THIS record
        ra, rb = ms.records.get(nm), it.records.get(nm)
        exp_ms, exp_it = SELFTEST_SIZES[nm]
        want_div = nm in SELFTEST_EXPECT_DIVERGENT
        got_div = nm in divnames
        detail = ""
        if ra is None or rb is None:
            fails.append("%s: not laid out on %s" % (nm, "MS" if ra is None else "Itanium"))
            w("%-16s %-10s %-10s %-12s %-12s %s\n"
              % (nm, ra.size if ra else "-", rb.size if rb else "-",
                 "%d/%d" % (exp_ms, exp_it), "FAIL", "record missing"))
            continue
        if ra.size != exp_ms:
            mine.append("%s: MS sizeof=%d, expected %d" % (nm, ra.size, exp_ms))
        if rb.size != exp_it:
            mine.append("%s: IT sizeof=%d, expected %d" % (nm, rb.size, exp_it))
        if want_div and not got_div:
            mine.append("%s: KNOWN-DIVERGENT shape was NOT reported divergent "
                        "-- the tool cannot report a difference" % nm)
        if (not want_div) and got_div:
            mine.append("%s: KNOWN-IDENTICAL shape was reported divergent (%s)"
                        % (nm, byname[nm].kinds))
        if want_div and got_div:
            exp_field, exp_a, exp_b = SELFTEST_FIRST[nm]
            got = byname[nm].first
            detail = "first divergent field %s" % (got,)
            if got is None or got[0] != exp_field or got[1] != exp_a or got[2] != exp_b:
                mine.append("%s: first divergent field %s, expected ('%s', %d, %d)"
                            % (nm, got, exp_field, exp_a, exp_b))
        fails.extend(mine)
        w("%-16s %-10d %-10d %-12s %-12s %s\n"
          % (nm, ra.size, rb.size, "%d/%d" % (exp_ms, exp_it),
             ("DIVERGENT" if got_div else "identical") + ("" if not mine else " FAIL"),
             detail))

    # armed floors that do not belong to any single record
    if ncmp != len(SELFTEST_NAMES):
        fails.append("compared %d records, expected %d (a differ that parses nothing "
                     "reports no divergence)" % (ncmp, len(SELFTEST_NAMES)))
    if missing:
        fails.append("asymmetric records in the self-test corpus: %s" % (missing,))
    if divnames != SELFTEST_EXPECT_DIVERGENT:
        fails.append("divergent set was %s, expected exactly %s"
                     % (sorted(divnames), sorted(SELFTEST_EXPECT_DIVERGENT)))

    # independent second oracle: ShowSize<> (no layout dump involved)
    w("\nPROBE CROSS-CHECK (independent oracle -- ShowSize<>, no layout dump)\n")
    pms = probe_side(args._clang, args.ms_target, src, SELFTEST_NAMES, args._ms_extra,
                     workdir, "st_ms")
    pit = probe_side(args._clang, it_target, src, SELFTEST_NAMES, args._it_extra,
                     workdir, "st_it")
    w("%-16s %-16s %-16s %s\n" % ("RECORD", "MS probe sz/al", "IT probe sz/al", "vs dump"))
    w("-" * 72 + "\n")
    for nm in SELFTEST_NAMES:
        a, b = pms.get(nm), pit.get(nm)
        ra, rb = ms.records.get(nm), it.records.get(nm)
        ok = (a is not None and b is not None and ra is not None and rb is not None
              and a[0] == ra.size and a[1] == ra.align
              and b[0] == rb.size and b[1] == rb.align)
        w("%-16s %-16s %-16s %s\n" % (nm, "%s/%s" % a if a else "-",
                                      "%s/%s" % b if b else "-", "agree" if ok else "MISMATCH"))
        if not ok:
            fails.append("%s: probe oracle %s/%s disagrees with dump oracle %s/%s"
                         % (nm, a, b,
                            (ra.size, ra.align) if ra else None,
                            (rb.size, rb.align) if rb else None))

    w("\n" + "=" * 80 + "\n")
    if fails:
        w("SELF-TEST FAILED -- %d problem(s):\n" % len(fails))
        for f in fails:
            w("  * %s\n" % f)
        w("A tool that cannot report a difference is worse than no tool. "
          "Do not trust any run from this build.\n")
        return 3
    w("SELF-TEST PASS\n")
    w("  reported DIVERGENT (and required to): %s\n" % sorted(SELFTEST_EXPECT_DIVERGENT))
    w("  reported IDENTICAL (and required to): %s\n"
      % sorted(set(SELFTEST_NAMES) - SELFTEST_EXPECT_DIVERGENT))
    w("  both outcomes occurred in this single run, so 'no divergence' is a real result\n"
      "  and not the only thing this instrument can say.\n")
    return 0


# ---------------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rt-layout-diff.py",
        description="Single-clang MS-ABI vs Itanium-ABI record layout audit. "
                    "DIVERGENCE IS NOT A BUG -- it flags candidates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit: 0 clean / 1 divergences found / 2 tool error / 3 self-test failed")
    ap.add_argument("input", nargs="?", help="header or TU to audit")
    ap.add_argument("--clang",
                    help="clang.exe to use (default: rt1 build/bin/clang.exe). An "
                         "AUTO-DISCOVERED compiler must report an rt1 version string "
                         "(working rule 13); passing --clang is the deliberate override and "
                         "is recorded in the report header.")
    ap.add_argument("--ms-target", default=DEFAULT_MS_TARGET)
    ap.add_argument("--it-target", default=DEFAULT_IT_TARGET,
                    help="MUST be the same architecture as --ms-target")
    ap.add_argument("--records",
                    help="comma-separated record names to FORCE complete, instead of "
                         "auto-discovery. Note this selects what is instantiated, not what "
                         "is compared: every record the TU lays out is compared.")
    ap.add_argument("--no-instantiate", action="store_true",
                    help="compile the input directly instead of generating a driver TU "
                         "(only records the TU already uses will be laid out)")
    ap.add_argument("--divergent-only", action="store_true",
                    help="omit the identical records from the table (they are printed by "
                         "default because they are the evidence the tool can say 'identical')")
    ap.add_argument("--probe", action="store_true",
                    help="also run the independent ShowSize<> sizeof/alignof oracle")
    ap.add_argument("--short-wchar", action="store_true",
                    help="add -fshort-wchar to the Itanium side (removes the one MEASURED "
                         "non-record-layout scalar difference on the default triple pair)")
    ap.add_argument("-I", dest="incdirs", action="append", default=[],
                    help="include directory (repeatable), passed to BOTH sides")
    ap.add_argument("-D", dest="defines", action="append", default=[],
                    help="preprocessor define (repeatable), passed to BOTH sides")
    ap.add_argument("--std", help="e.g. c++14 -- passed to BOTH sides")
    ap.add_argument("--extra", action="append", default=[],
                    help="extra flag for BOTH sides (repeatable)")
    ap.add_argument("--ms-extra", action="append", default=[], help="extra flag, MS side only")
    ap.add_argument("--it-extra", action="append", default=[],
                    help="extra flag, Itanium side only")
    ap.add_argument("--workdir", help="where to put temporaries (default: a fresh dir under "
                                      "%%TEMP%%). Never /tmp.")
    ap.add_argument("--keep", action="store_true", help="keep the workdir")
    ap.add_argument("--json", dest="jsonout", help="also write machine-readable results here")
    ap.add_argument("--layoutcmp-dir", default=os.path.join(REPO, "scratch", "FUZZ"),
                    help="directory containing the banked layoutcmp.py")
    ap.add_argument("--self-test", action="store_true",
                    help="run the armed self-test (must report a known divergent AND a known "
                         "identical shape in one run) and exit")
    ap.add_argument("--self-test-break",
                    choices=["vacuous-target", "blind", "noisy", "deaf"],
                    help="deliberately break the tool to prove the self-test can FAIL: "
                         "vacuous-target = compile both sides with the MS triple; "
                         "blind = comparator reports nothing; "
                         "noisy = comparator reports everything; "
                         "deaf = parser returns no records")
    args = ap.parse_args(argv)

    try:
        args._clang = find_clang(args.clang)
        # Identity arm BEFORE anything is compiled or measured (working rule 13).
        args._clang_version = arm_identity(args._clang, bool(args.clang))
    except ToolError as e:
        sys.stderr.write("rt-layout-diff: %s\n" % e)
        return 2

    lc = load_layoutcmp(args.layoutcmp_dir)

    common = []
    if args.std:
        common.append("-std=" + args.std)
    common += ["-I" + d for d in args.incdirs]
    common += ["-D" + d for d in args.defines]
    common += list(args.extra)
    args._ms_extra = common + list(args.ms_extra)
    args._it_extra = common + list(args.it_extra) + (["-fshort-wchar"] if args.short_wchar
                                                     else [])

    if args.workdir:
        os.makedirs(args.workdir, exist_ok=True)
        workdir = os.path.abspath(args.workdir)
        made = False
    else:
        workdir = tempfile.mkdtemp(prefix="rt-layout-diff-")   # honours %TEMP%, never /tmp
        made = True
    args._workdir = workdir

    rc = 2
    try:
        if args.self_test:
            rc = self_test(args, lc)
            return rc

        if not args.input:
            ap.error("input is required unless --self-test is given")
        inp = os.path.abspath(args.input)
        if not os.path.isfile(inp):
            raise ToolError("input %s does not exist" % inp)
        args._input = inp

        if args.ms_target.split("-")[0] != args.it_target.split("-")[0]:
            sys.stderr.write(
                "rt-layout-diff: WARNING: --ms-target arch %r != --it-target arch %r.\n"
                "  Ordinary pointer-size/alignment differences will masquerade as ABI\n"
                "  divergence.  Use an arch-matched pair.\n"
                % (args.ms_target.split("-")[0], args.it_target.split("-")[0]))

        # Both sides must compile the input BEFORE anything is attributed to layout.
        preflight(args._clang, args.ms_target, inp, args._ms_extra, workdir, "ms")
        preflight(args._clang, args.it_target, inp, args._it_extra, workdir, "it")

        if args.records:
            names = [n.strip() for n in args.records.split(",") if n.strip()]
        elif args.no_instantiate:
            names = None
        else:
            # union of both sides: a record that only exists under #ifdef _WIN32 must still
            # reach the comparison, where it is reported as ASYMMETRIC rather than vanishing.
            a = discover_records(args._clang, args.ms_target, inp, args._ms_extra,
                                 workdir, "ms")
            b = discover_records(args._clang, args.it_target, inp, args._it_extra,
                                 workdir, "it")
            names = a + [n for n in b if n not in set(a)]
            if not names:
                raise ToolError("no record definitions discovered in %s; pass --records" % inp)

        ms = build_side(lc, args._clang, "ms", args.ms_target, inp, names, args._ms_extra,
                        workdir, args.no_instantiate)
        it = build_side(lc, args._clang, "it", args.it_target, inp, names, args._it_extra,
                        workdir, args.no_instantiate)

        allnames = sorted(set(ms.records) | set(it.records))
        ncmp, divs, missing = compare_sides(lc, ms, it, allnames)

        # ARMED FLOOR ON THE PRODUCTION PATH (CLAUDE.md working rule 3).
        # --self-test already treats "compared 0 records" as a FAILURE ("a differ that parses
        # nothing reports no divergence").  The shipped run path did not, so a run that
        # compared NOTHING printed "VERDICT: no divergence" and exited 0 -- indistinguishable
        # from a clean audit.  MEASURED (verifier repro dupname.cpp, this session): an input
        # whose only laid-out record IS divergent gave "records compared: 0 ... VERDICT: no
        # divergence", EXIT 0, because both copies of the name were ambiguity-poisoned.
        # Zero comparisons is never a result; it is a tool/input error.  Exit 2, not 0.
        if ncmp == 0:
            amb = sorted(set(ms.ambiguous) | set(it.ambiguous))
            raise ToolError(
                "VACUOUS RUN -- ZERO records were compared, so 'no divergence' would mean\n"
                "  nothing.  This is reported as a tool/input error (exit 2), never as a\n"
                "  clean result.  MS laid out %d record(s), Itanium %d, common 0.\n"
                "  ambiguous names excluded: %s\n"
                "  not nameable at global scope: MS=%s IT=%s\n"
                "  asymmetric (one side only): %d\n"
                "  Dumps kept for inspection: %s , %s\n"
                "  Typical fixes: name the records with --records (qualified names work),\n"
                "  drop --no-instantiate, or check that both sides see the same #ifdefs."
                % (len(ms.records), len(it.records), amb or "-",
                   ms.dropped or "-", it.dropped or "-", len(missing),
                   ms.dumpfile, it.dumpfile))

        probes = None
        if args.probe:
            pnames = names if names else [n for n in allnames if "(" not in n and "::" not in n]
            probes = (probe_side(args._clang, args.ms_target, inp, pnames, args._ms_extra,
                                 workdir, "ms"),
                      probe_side(args._clang, args.it_target, inp, pnames, args._it_extra,
                                 workdir, "it"),
                      pnames)

        render(args, ms, it, ncmp, divs, missing, probes, allnames)

        if args.jsonout:
            blob = {
                "clang": args._clang, "clang_version": args._clang_version,
                "clang_explicit": bool(args.clang),
                "ms_target": ms.target, "it_target": it.target,
                "input": inp, "compared": ncmp, "records": allnames,
                "divergent": [
                    {"record": d.name, "ms_size": d.ms.size, "ms_align": d.ms.align,
                     "it_size": d.it.size, "it_align": d.it.align,
                     "kinds": d.kinds,
                     "first_divergent_field": (
                         {"field": d.first[0], "ms_bit": d.first[1], "it_bit": d.first[2]}
                         if d.first else None)}
                    for d in divs],
                "asymmetric": [{"record": n, "missing_on": "MS" if a else "Itanium"}
                               for n, a, b in missing],
                "ambiguous_not_compared": sorted(set(ms.ambiguous) | set(it.ambiguous)),
            }
            with open(args.jsonout, "w", encoding="utf-8") as f:
                json.dump(blob, f, indent=2)
            if not os.path.isfile(args.jsonout) or os.path.getsize(args.jsonout) == 0:
                raise ToolError("--json artifact %s missing or empty" % args.jsonout)

        rc = 1 if divs else 0
        return rc
    except ToolError as e:
        sys.stderr.write("rt-layout-diff: ERROR: %s\n" % e)
        rc = 2
        return rc
    except Exception as e:                                   # parser strictness surfaces here
        sys.stderr.write("rt-layout-diff: ERROR: %s: %s\n" % (type(e).__name__, e))
        rc = 2
        return rc
    finally:
        if made and not args.keep and rc != 2:
            shutil.rmtree(workdir, ignore_errors=True)
        elif made:
            sys.stderr.write("rt-layout-diff: workdir kept at %s\n" % workdir)


if __name__ == "__main__":
    sys.exit(main())
