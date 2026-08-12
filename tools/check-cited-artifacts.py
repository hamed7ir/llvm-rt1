#!/usr/bin/env python3
# rt1 --- CONTINUOUS CITED-ARTIFACT TRACKING CHECK.  Working rules 1, 3, 8.
#
# ENABLE THE PRE-COMMIT HOOK WITH EXACTLY THIS ONE LINE (the user runs it, not the assistant --
# enabling a hook changes how every future commit in this clone behaves):
#
#     git config core.hooksPath .githooks
#
# ---------------------------------------------------------------------------------------------
# WHY THIS EXISTS (MEASURED, 2026-08-10)
#
#   Working rule 1 says every claim cites an artifact.  An artifact a reader cannot obtain from a
#   fresh clone is evidence in /tmp, whatever directory it happens to sit in.  This project has
#   now hit that defect FOUR times, and the fourth is the one that makes a one-shot sweep
#   insufficient:
#
#     09677eb  stage/MODIFICATIONS.txt -- a SHIPPING Apache-2.0 notice, untracked.
#     315965f  A4 swept 219 cited paths and banked 19 more that were outside version control.
#     552cbec  "A4's class again, 20 minutes after A4 shipped": a NEW document cited
#              scratch/UP1/passname-probe.ll, which `scratch/**/*.ll` swallowed.  Caught only
#              because `git add` happened to refuse and print a hint.
#     dc67dc0  "third occurrence": the U3 port deliverables.
#
#   A file created AFTER a sweep is invisible to that sweep BY CONSTRUCTION.  One-time sweeps do
#   not hold in a repo that keeps producing evidence, so the check has to run on every commit.
#
# ---------------------------------------------------------------------------------------------
# TWO DESIGN DECISIONS THAT ARE LOAD-BEARING.  Read before changing anything.
#
# (1) TRACKING AUTHORITY IS `git ls-files`, NEVER `git check-ignore`.
#     MEASURED this run: `git check-ignore -v scratch/UP1/passname-probe.ll` exits 1, and
#     `git check-ignore --stdin --no-index` over the whole tracked corpus returns 0 paths.
#     check-ignore CONSULTS THE INDEX by default -- it answers "would git have ignored this if it
#     were not already tracked", which is a different question from "is this in version control".
#     It is used in this script for ONE thing only: producing the remediation hint on a path that
#     has ALREADY been proven untracked by ls-files.  It is never an authority.
#
# (2) "MATCHED BY .gitignore" IS NOT AN EXEMPTION.  This is the whole point.
#     The incident file scratch/UP1/passname-probe.ll WAS matched by an ignore rule
#     (`scratch/**/*.ll`) -- that match WAS the bug.  A check that exempted ignored paths would
#     have passed the very defect it exists to catch: gate-vacuity (rule 3).
#     So exemption is an EXPLICIT, ENUMERATED allowlist (EXEMPT below), derived from the
#     categories .gitignore's own comments already draw, and it FAILS CLOSED: a newly added broad
#     ignore rule silently exempts NOTHING.  Anything cited and untracked that is not in that
#     enumerated list is an AUTHORED artifact and is a failure.
#
# ---------------------------------------------------------------------------------------------
# CORPUS RULE: every path set here comes from `git ls-files` (the INDEX).  Never a filesystem
# walk -- llvm-project/ and scratch/UP1/main-src/ hold 100k+ files each, and every sweep that
# walked the filesystem from the repo root hung for hours.
#
# Reading the INDEX rather than HEAD is what makes this correct as a pre-commit hook: a doc and
# the artifact it cites, staged in the same commit, both count as present.
#
# ---------------------------------------------------------------------------------------------
# USAGE
#   python tools/check-cited-artifacts.py              # check the repo as it stands
#   python tools/check-cited-artifacts.py --list       # ...and print every classified citation
#   python tools/check-cited-artifacts.py --extra-doc FILE.md
#                                                      # also scan a doc that is not in the index
#   python tools/check-cited-artifacts.py --selftest   # ARMED FLOOR: prove the check can FAIL
#
# EXIT CODES
#   0  no authored artifact is cited-but-untracked
#   1  at least one is  (the pre-commit hook blocks the commit)
#   2  the check itself could not run (not a git repo, git missing, ...)

import os
import re
import subprocess
import sys

# ==============================================================================================
# EXEMPT -- deliberately-untracked paths.  Categories and rationale are REUSED from .gitignore's
# own comments; the quoted fragments below are that file's wording.  Glob syntax: ** = any depth.
#
# Adding an entry here is a decision that a cited path is NOT authored evidence.  Every entry
# names the category and why.  If you are tempted to add a pattern to silence a failure on
# something this project WROTE, the fix is the other one: track the file.
# ==============================================================================================
EXEMPT = [
    # ---- A. third-party source trees: downloaded or externally owned, not authored here -------
    # ---- DANGLING BY DESIGN: evidence LOCATIONS in trees this repo does not contain ---------
    # DISPOSITION-TABLE.md cites these to say WHERE a measurement was taken. They are upstream
    # LLVM source and consumer-browser source, not artifacts this repository could ship, and a
    # reader resolves them against those projects. Enumerated here so a future reader sees they
    # are DELIBERATE, not files someone forgot to copy across during curation.
    ("compiler-rt/**",             "upstream-source", "upstream LLVM: cited as an evidence location"),
    ("llvm/**",                    "upstream-source", "upstream LLVM: cited as an evidence location"),
    ("clang/**",                   "upstream-source", "upstream LLVM: cited as an evidence location"),
    ("lld/**",                     "upstream-source", "upstream LLVM: cited as an evidence location"),
    ("js/**",                      "consumer-source", "consumer browser tree: cited as an evidence location"),
    ("gfx/**",                     "consumer-source", "consumer browser tree: cited as an evidence location"),
    ("uxp/**",                     "consumer-source", "consumer browser tree: cited as an evidence location"),
    ("GT/**",                      "shell-variable",  "a $GT-expanded path inside a quoted command line, not a repo path"),
    ("arm/**",                     "consumer-source", "consumer tree: cited as an evidence location"),
    ("llvm-project/**",            "3rd-party-tree",  ".gitignore: 'its own git repo ... Clone llvmorg-18.1.8 and apply patches/'"),
    ("clang21/**",                 "3rd-party-tree",  ".gitignore: official LLVM package, downloaded not authored"),
    ("clang22/**",                 "3rd-party-tree",  ".gitignore: 'official LLVM 22.1.8 win64 package, downloaded not authored'"),
    ("scratch/UP1/main-src/**",    "3rd-party-tree",  ".gitignore: \"U1's upstream main build -- downloaded source\""),
    ("scratch/UP1/main.tar.gz",    "3rd-party-tree",  ".gitignore: same; reproducible from scratch/UP1/MAIN-COMMIT.txt"),
    ("scratch/T6/verify-tree/**",  "3rd-party-tree",  ".gitignore: 'T6 verification worktree (100k+ files, never commit)'"),
    # Retired BUILD OUTPUT, not evidence: holds bin-STALE-<commit>/ -- superseded driver binaries
    # moved aside rather than deleted so a stale set can never be mistaken for the shipped one.
    # RT1-WORKLOG.md cites the directory to say where they went, which is a claim about
    # housekeeping, not an artifact a reader needs to open.
    ("scratch/UP1/retired/**",     "build-output",    "retired stale binaries; cited as a location, not as evidence"),
    # PKG-1 build output. dist/ holds the 209 MB archive and dist/verify/ a throwaway extraction
    # of it. RT1-PKG-1.md cites the extraction to say WHERE the verification ran; it is a
    # location, not evidence a reader needs to open. The artifact worth keeping is the manifest,
    # scratch/VOICE/pkg-manifest.tsv, which IS tracked -- and from it plus stage/ both are
    # regenerable byte-for-byte.
    ("dist/**",                    "build-output",    "PKG-1 archive + throwaway extraction; regenerable from stage/ + the tracked manifest"),
    ("dist/verify/",               "build-output",    "PKG-1 throwaway extraction; cited as a location, not as evidence"),
    ("scratch/UP1/retired/",       "build-output",    "retired stale binaries; cited as a location, not as evidence"),
    # "Fetched upstream branch sources (W5a/W5b/W6 sweeps) -- downloaded, not authored".
    # Extension-scoped ON PURPOSE: the same .gitignore stanza says "The REPORTS in these
    # directories are authored and ARE tracked", so *.md there stays subject to the check.
    ("scratch/W5a/*.cpp",          "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W5a/*.h",            "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W5a/bug5/branch-files/**", "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W5a/rebase/**",      "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W5a/verify/**",      "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W5b/**",             "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/*.cpp",           "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/*.h",             "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/*.td",            "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/*.cmake",         "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/*.patch",         "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/W6/verify/**",       "3rd-party-fetch", ".gitignore: fetched upstream branch source"),
    ("scratch/UP1/gh_*.cpp",       "3rd-party-fetch", ".gitignore: fetched upstream source"),
    ("upstream-check/*.cpp",       "3rd-party-fetch", ".gitignore: fetched branch files (RLB.release_21.x.cpp is the banked exception and IS tracked)"),
    ("scratch/W*/*.obj",           "3rd-party-owned", ".gitignore: \"Microsoft's, extracted from libcmt.lib -- NOT ours to redistribute\""),

    # ---- B. build output / regenerable ---------------------------------------------------------
    ("build*/**",                  "build-output",    ".gitignore: 'Build outputs and the extracted third-party toolchains'"),
    ("stage/**",                   "build-output",    ".gitignore: build output (stage/MODIFICATIONS.txt is the authored exception and IS tracked)"),
    ("scratch/UP1/main-build/**",  "build-output",    ".gitignore: upstream main build tree"),
    ("scratch/F0-4/tmp/**",        "build-output",    ".gitignore: \"clang's auto-generated preprocessed crash dumps (MBs each)\""),
    ("**/__pycache__/**",          "build-output",    ".gitignore: compiled leftovers"),
    ("scratch/R6/CLEANIR.ll",      "build-output",    ".gitignore: 29 MB whole-module IR dump, 'cited by nothing and ... regenerable from the R6 harness'"),
    ("scratch/R6/DIRTYIR.ll",      "build-output",    ".gitignore: as above"),

    # ---- C. per-run / local state -------------------------------------------------------------
    ("memory/**",                  "local-state",     ".gitignore: 'assistant state, not a project deliverable'"),
    ("scratch/**/.armed*",         "local-state",     ".gitignore: 'Rule-13 identity-arm sentinels/stamps. Per-run state, never committed'"),
    (".git/**",                    "local-state",     "git internals"),
    (".claude/**",                 "local-state",     "harness-local settings"),
]

# Binary / bulk EXTENSIONS that .gitignore excludes wherever they appear ("Bulk artifacts",
# "Compiled leftovers", "Rebuilt compilers used as mutants ... 29 MB each", "the 398 MB trap").
# A citation of one of these is a citation of a build product, not of authored evidence.
EXEMPT_EXT = {
    ".obj", ".pdb", ".exe", ".dll", ".lib", ".zip", ".dmp", ".o", ".pyc", ".gz", ".xz",
}

# Extensions that make a bare, slash-free token (e.g. "peicheck2.py") worth resolving at all.
KNOWN_EXT = {
    ".md", ".py", ".sh", ".c", ".cpp", ".cc", ".h", ".hpp", ".ll", ".mir", ".s", ".asm",
    ".txt", ".json", ".bat", ".patch", ".diff", ".log", ".csv", ".bin", ".td", ".cmake",
    ".yaml", ".yml", ".ini", ".cfg", ".toml", ".rst", ".def", ".inc", ".test", ".cfi",
} | EXEMPT_EXT

# Top-level directories of the upstream monorepo.  A citation like
# "llvm/lib/Target/ARM/ARMISelLowering.cpp:2423" is an UPSTREAM path (rule 7 requires the tree be
# named); it resolves under llvm-project/ and is third-party.  Verified by a single stat, never a walk.
UPSTREAM_ROOTS = (
    "llvm/", "clang/", "lld/", "compiler-rt/", "libcxx/", "libcxxabi/", "libunwind/", "mlir/",
    "flang/", "polly/", "lldb/", "openmp/", "bolt/", "clang-tools-extra/", "third-party/",
    "cmake/", "runtimes/", "utils/",
)


def sh(args):
    """Run git, return stdout.  Fail loudly -- a check that cannot run must not report success."""
    try:
        p = subprocess.run(args, capture_output=True, text=False)
    except OSError as e:
        print("check-cited-artifacts: FATAL: cannot exec %s: %s" % (args[0], e), file=sys.stderr)
        sys.exit(2)
    if p.returncode != 0 and args[:2] != ["git", "check-ignore"]:
        print("check-cited-artifacts: FATAL: %s exited %d\n%s"
              % (" ".join(args), p.returncode, p.stderr.decode("utf-8", "replace")), file=sys.stderr)
        sys.exit(2)
    return p.stdout.decode("utf-8", "replace")


def glob_to_re(pat):
    """Translate the ** / * glob subset used in EXEMPT into a regex.  '*' never crosses '/'."""
    out, i = [], 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


# Each EXEMPT entry compiles to TWO regexes: the pattern itself, and -- only for patterns ending
# in '/**' -- the bare directory it covers, so a citation of "stage/" matches "stage/**".
#
# MEASURED DEFECT IN THIS SCRIPT, caught by auditing the exempt bucket rather than by the
# pass/fail count (rule 15: arm on IDENTITY, not on counts).  The first version tried
# `rx.match(t) or rx.match(t + "/")` as that directory fallback.  That made "build*/**" -> regex
# "build[^/]*/.*" match the bare authored filename "build-aeabi-shim.sh": appending "/" gave
# "build-aeabi-shim.sh/", where "[^/]*" happily ate "-aeabi-shim.sh".  A FALSE EXEMPTION -- the
# one direction that silently resurrects the defect class this check exists to catch, and the
# totals looked entirely healthy while it was happening.
def _dir_re(pat):
    return glob_to_re(pat[:-3]) if pat.endswith("/**") else None


EXEMPT_RE = [(glob_to_re(p), _dir_re(p), cat, why) for p, cat, why in EXEMPT]

# ----------------------------------------------------------------------------------------------
# Extraction.
#
# Strip first, then match -- URLs and Windows absolute paths contain slashes and dots and would
# otherwise produce a stream of phantom citations.
# ----------------------------------------------------------------------------------------------
URL_RE = re.compile(r"""\b[a-z][a-z0-9+.\-]*://\S+""", re.I)
WINABS_RE = re.compile(r"""\b[A-Za-z]:[\\/][^\s`'"|)\]]*""")
FENCE_RE = re.compile(r"^\s*```")

# repo-relative path with at least one '/', or a bare name; trailing '/' marks a directory ref.
TOKEN_RE = re.compile(r"""(?<![\w/.\-])((?:[\w.\-+@]+/)+[\w.\-+@]*|[\w.\-+@]+\.[A-Za-z][\w]{0,7})""")

# A token carrying any of these is a pattern/placeholder/command fragment, not a citation.
META_RE = re.compile(r"""[*?\[\]<>${}!|]""")


def strip_noise(line):
    line = URL_RE.sub(" ", line)
    line = WINABS_RE.sub(" ", line)
    return line


def clean_token(tok):
    """Trim citation decoration: :LINE, :LINE-LINE, #NNN, and trailing prose punctuation."""
    tok = re.sub(r":\d+(?:[-:]\d+)?$", "", tok)
    tok = re.sub(r"#\d+$", "", tok)
    tok = tok.rstrip(".,;:'\"`)]}")
    return tok


def is_pathlike(tok):
    """The task's definition: a repo-relative path WITH AN EXTENSION, or a DIRECTORY REFERENCE."""
    if not tok or META_RE.search(tok):
        return False
    if tok.startswith("/") or tok.startswith("./") or tok.startswith("../"):
        return False
    segs = [s for s in tok.split("/") if s]
    # ":543/:614/:615" -- a multi-line citation of ONE file (this project writes them that way,
    # see the Bug-2 precedent in CLAUDE.md).  The regex sees "543/" as a directory reference.
    if any(s.isdigit() for s in segs):
        return False
    # "release/22.x", "main/23.x" -- upstream BRANCH names, not paths.
    if len(segs) == 2 and re.match(r"^\d+\.x$", segs[-1]):
        return False
    if tok.endswith("/"):                      # directory reference
        return len(tok) > 1
    ext = os.path.splitext(tok)[1].lower()
    if not ext or not re.match(r"^\.[A-Za-z]", ext):   # rejects "18.1.8", "v1.2"
        return False
    if "/" in tok:
        return True
    return ext in KNOWN_EXT                    # bare filename: only with a known extension


def extract(path, text):
    """Yield (lineno, token).  Fenced code blocks are scanned too -- the A4 incident path was
    cited inside backticks -- but META_RE drops the glob/placeholder noise that lives there."""
    seen = set()
    for n, raw in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(raw):
            continue
        for m in TOKEN_RE.finditer(strip_noise(raw)):
            tok = clean_token(m.group(1))
            if is_pathlike(tok) and (tok, n) not in seen:
                seen.add((tok, n))
                yield n, tok


def exempt_reason(tok):
    """tok keeps its trailing '/' if the document wrote it as a directory reference."""
    t = tok.rstrip("/")
    # The directory form of an 'X/**' pattern is only tried when the citation REALLY denotes a
    # directory -- written with a trailing '/', or present on disk as one.  Second half of the
    # false-exemption defect above: restricting the fallback to '/**' patterns was not enough,
    # because _dir_re('build*/**') is '^build[^/]*$', which still matches the bare authored file
    # 'build-aeabi-shim.sh'.  A wildcard directory pattern can always impersonate a filename, so
    # the guard has to be on the CITATION's shape, not on the pattern's.
    as_dir = tok.endswith("/") or os.path.isdir(t)
    for rx, drx, cat, why in EXEMPT_RE:
        if rx.match(t) or (as_dir and drx is not None and drx.match(t)):
            return cat, why
    if os.path.splitext(t)[1].lower() in EXEMPT_EXT:
        return "build-output", ".gitignore bulk/binary artifact extension"
    if t.startswith(UPSTREAM_ROOTS) and os.path.exists(os.path.join("llvm-project", t)):
        return "upstream-tree", "resolves under llvm-project/ (third-party source tree)"
    return None


def main(argv):
    show_list = "--list" in argv
    staged_only = "--staged" in argv
    extra = [argv[i + 1] for i, a in enumerate(argv) if a == "--extra-doc" and i + 1 < len(argv)]

    root = sh(["git", "rev-parse", "--show-toplevel"]).strip()
    if not root:
        print("check-cited-artifacts: FATAL: not a git repository", file=sys.stderr)
        return 2
    os.chdir(root)

    # --- CORPUS: the index, never a filesystem walk -------------------------------------------
    tracked = set(p for p in sh(["git", "ls-files", "-z"]).split("\0") if p)
    tracked_dirs = set()
    for p in tracked:
        parts = p.split("/")
        for i in range(1, len(parts)):
            tracked_dirs.add("/".join(parts[:i]))
    basename_index = {}
    for p in tracked:
        basename_index.setdefault(os.path.basename(p), []).append(p)

    # --staged is the PRE-COMMIT scope: only the .md documents in THIS commit.
    #
    # Why the hook is not full-repo.  rt1 has a real backlog of cited-but-untracked artifacts
    # (26 at the time this was written).  A hook that blocks every commit until the backlog is
    # cleared gets turned off within the hour, and a disabled check is worth exactly nothing --
    # the same "unsound instruments are QUARANTINED loudly, never silently dropped" problem
    # arriving through the side door.  Scoping to staged docs catches the case that actually
    # recurred FOUR times: a NEW OR EDITED document citing an artifact that is not in the index.
    #
    # KNOWN GAP, stated rather than hidden: this scope cannot see a citation in a document that
    # is not part of this commit -- e.g. if an artifact is `git rm`'d while the doc citing it is
    # left alone.  Full-repo mode (no --staged) is the periodic audit that closes it; run it
    # before a release.
    if staged_only:
        out = sh(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z", "--", "*.md"])
        docs = [p for p in out.split("\0") if p and os.path.exists(p)]
    else:
        docs = [p for p in sorted(tracked) if p.lower().endswith(".md")]
    docs = docs + list(extra)

    fails, exempted, ok, unresolved = [], 0, 0, []
    listing = []
    ntok = 0

    for doc in docs:
        try:
            with open(doc, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print("check-cited-artifacts: FATAL: cannot read %s: %s" % (doc, e), file=sys.stderr)
            return 2
        for lineno, tok in extract(doc, text):
            ntok += 1
            t = tok.rstrip("/")
            isdir = tok.endswith("/")

            if t in tracked or (isdir and t in tracked_dirs) or t in tracked_dirs:
                ok += 1
                listing.append(("TRACKED", tok, doc, lineno, ""))
                continue

            er = exempt_reason(tok)
            if er:
                exempted += 1
                listing.append(("EXEMPT", tok, doc, lineno, er[0]))
                continue

            # Bare filename with no directory component: resolve against the tracked corpus.
            if "/" not in t:
                hits = basename_index.get(t, [])
                if hits:
                    ok += 1
                    listing.append(("TRACKED", tok, doc, lineno, "basename->%s" % hits[0]))
                elif os.path.exists(t):
                    fails.append((tok, doc, lineno, "UNTRACKED", os.path.getsize(t)))
                else:
                    unresolved.append((tok, doc, lineno))
                    listing.append(("UNRESOLVED", tok, doc, lineno, "no tracked basename match"))
                continue

            if os.path.exists(t):
                sz = os.path.getsize(t) if os.path.isfile(t) else -1
                fails.append((tok, doc, lineno, "UNTRACKED", sz))
            else:
                unresolved.append((tok, doc, lineno))
                listing.append(("UNRESOLVED", tok, doc, lineno, "not on disk, not in index"))

    if show_list:
        for kind, tok, doc, lineno, note in listing:
            print("  %-10s %-52s %s:%d %s" % (kind, tok, doc, lineno, note))

    # ------------------------------------------------------------------------------------------
    # Report.  Rule 8's lesson: any sweep reporting a count must also report its DENOMINATOR,
    # or a sweep that never ran reads identically to a clean one.
    # ------------------------------------------------------------------------------------------
    print("cited-artifact check  |  docs scanned: %d (of %d tracked files)  |  citations: %d"
          % (len(docs), len(tracked), ntok))
    print("  tracked: %d   exempt (3rd-party/build/local): %d   unresolved (advisory): %d   FAIL: %d"
          % (ok, exempted, len(unresolved), len(fails)))

    # ADVISORY, never fatal.  "Unresolved" means the path is neither on disk nor in the index, so
    # it CANNOT be the defect this check hunts (an authored file sitting outside version control).
    # It is split because only one half is actionable: a slash-bearing repo-relative path that has
    # gone stale, versus a bare basename, which in this project is almost always an upstream file
    # named in prose ("ARMISelLowering.cpp") and is a rule-7 style question, not a tracking one.
    if unresolved:
        rel = [u for u in unresolved if "/" in u[0]]
        print("  advisory: %d stale repo-relative citation(s), %d bare basename(s) in prose"
              % (len(rel), len(unresolved) - len(rel)))
        if show_list:
            for tok, doc, lineno in rel:
                print("    %-52s %s:%d" % (tok, doc, lineno))

    if not fails:
        # Report the DENOMINATOR, never a bare green.  Rule 8's lesson: a sweep that never ran
        # reads identically to a clean result unless it states its coverage.  In --staged mode a
        # commit that touches no .md scans nothing, and "PASS: every artifact is tracked" would
        # be a claim about 0 documents dressed up as a clean bill of health.
        if not docs:
            print("\nNOTHING CHECKED: no .md document is in scope (0 scanned). Not a pass.")
        elif not ntok:
            print("\nNOTHING CHECKED: %d document(s) in scope, but 0 citations found. Not a pass."
                  % len(docs))
        else:
            print("\nPASS: %d citation(s) across %d document(s); every authored artifact is in"
                  " version control." % (ntok, len(docs)))
        return 0

    print("\nFAIL: %d AUTHORED artifact(s) cited by a tracked document but NOT in version control."
          % len(fails))
    print("An artifact a reader cannot obtain from a fresh clone is evidence in /tmp.\n")
    for tok, doc, lineno, why, sz in sorted(set(fails)):
        print("  %s   (%s, %s bytes)" % (tok, why, sz if sz >= 0 else "dir"))
        print("      cited by: %s:%d" % (doc, lineno))
        ci = subprocess.run(["git", "check-ignore", "-v", tok], capture_output=True, text=True)
        if ci.returncode == 0 and ci.stdout.strip():
            # Diagnostic only -- ls-files above already settled that this path is untracked.
            print("      swallowed by: %s" % ci.stdout.strip())
            print("      fix: add a '!' negation to .gitignore WITH a rationale comment, then"
                  " `git add -f %s`" % tok)
        else:
            print("      fix: `git add %s`  (or add it to EXEMPT here if it is genuinely"
                  " third-party/build output)" % tok)
    return 1


def selftest():
    """ARMED FLOOR (rule 3): an instrument that cannot fail is not an instrument.

    This runs in a THROWAWAY GIT REPOSITORY, not in rt1.  That is deliberate and is the
    difference between arming the instrument and arming the repo:

      * rt1's own baseline is not clean -- it has real, pre-existing cited-but-untracked
        artifacts, which is precisely what the check is for.  Planting a positive here and
        reading the exit code would compare 1 against 1 and prove nothing (rule 4: one variable).
      * A temp repo gives a genuine PASS baseline, so the FAIL is attributable to the ONE thing
        that changed -- the planted citation.

    It also asserts the finding BY NAME, not by count.  Rule 15, MEASURED in this project: a
    detector can locate the right record and still label it wrong, and a count-based arm passes
    that defect completely.
    """
    import tempfile
    import shutil

    script = os.path.abspath(__file__)
    tmp = tempfile.mkdtemp(prefix="rt1-citedarm-")
    def run(*extra):
        p = subprocess.run([sys.executable, script] + list(extra),
                           cwd=tmp, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    try:
        # A repo whose .gitignore swallows evidence exactly the way rt1's does.
        with open(os.path.join(tmp, ".gitignore"), "w") as f:
            f.write("scratch/**/*.ll\n")
        os.makedirs(os.path.join(tmp, "scratch", "P"))
        bait = "scratch/P/planted-probe.ll"
        with open(os.path.join(tmp, bait), "w") as f:
            f.write("; planted positive for the cited-artifact armed floor\n")
        with open(os.path.join(tmp, "tracked-note.txt"), "w") as f:
            f.write("a tracked artifact\n")
        # NEGATIVE CONTROL: a doc citing only a TRACKED artifact.
        with open(os.path.join(tmp, "DOC.md"), "w") as f:
            f.write("# doc\n\nMEASURED: see `tracked-note.txt`.\n")
        for c in (["init", "-q"], ["add", "-A"],
                  ["-c", "user.email=a@b", "-c", "user.name=arm", "commit", "-qm", "base"]):
            subprocess.run(["git"] + c, cwd=tmp, capture_output=True)
        clean_rc, clean_out = run()

        # PLANT THE POSITIVE: one variable changes -- the doc now cites the ignored file.
        with open(os.path.join(tmp, "DOC.md"), "a") as f:
            f.write("\nMEASURED: reduction banked at `%s`.\n" % bait)
        armed_rc, armed_out = run()
        named = bait in armed_out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== ARMED FLOOR (isolated temp repo, one variable) ===")
    print("  negative control -- doc cites only a tracked file : exit %d  (expect 0)" % clean_rc)
    print("  planted positive -- doc cites ignored %s : exit %d  (expect 1)" % (bait, armed_rc))
    print("  positive named in the output BY NAME              : %s  (expect True)" % named)
    good = (clean_rc == 0 and armed_rc == 1 and named)
    print("  RESULT: %s" % (
        "ARMED -- passes clean, fails on a real positive, and names it correctly"
        if good else "BROKEN -- this check is VACUOUS, do not trust it"))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main(sys.argv))
