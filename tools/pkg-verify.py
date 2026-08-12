"""PKG-1 verification: run against an EXTRACTED archive, never against stage/ itself.

Three independent checks, each with its own failure mode named:

  1. FILE COUNT + MANIFEST      every file in the manifest is present, nothing extra is present.
                                A directory archive can silently gain files; a manifest cannot.
  2. SHA256 PER FILE            every extracted file matches the hash recorded at build time.
  3. COMMIT-STRING EXCLUSIVITY  every shipped .exe contains 7653a13d8..., and NO OTHER 40-hex
                                commit string.  This is the check that would have caught the
                                banked provenance trap where a tarball build embedded a commit
                                from an unrelated repository.

Usage:
    python tools/pkg-verify.py manifest <stagedir> <out.tsv>
    python tools/pkg-verify.py verify   <extractdir> <manifest.tsv>
"""
import hashlib, io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
RT1 = "7653a13d8d28189c7cef1401b934ec30d98ea353"
HEX40 = re.compile(rb"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])")


def walk(root):
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            yield os.path.relpath(p, root).replace("\\", "/"), p


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


mode = sys.argv[1]

if mode == "manifest":
    root, out = sys.argv[2], sys.argv[3]
    rows = [(rel, sha(p), os.path.getsize(p)) for rel, p in walk(root)]
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        "".join("%s\t%s\t%d\n" % r for r in rows))
    print("  manifest: %d files -> %s" % (len(rows), out))

elif mode == "verify":
    root, man = sys.argv[2], sys.argv[3]
    want = {}
    for line in io.open(man, encoding="utf-8"):
        rel, h, sz = line.rstrip("\n").split("\t")
        want[rel] = (h, int(sz))
    have = dict(walk(root))

    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    print("  [1] MANIFEST  expected %d, extracted %d, missing %d, EXTRA %d"
          % (len(want), len(have), len(missing), len(extra)))
    for m in missing[:10]:
        print("        MISSING %s" % m)
    for e in extra[:10]:
        print("        EXTRA   %s" % e)

    bad = []
    for rel, (h, sz) in want.items():
        if rel in have and sha(have[rel]) != h:
            bad.append(rel)
    print("  [2] SHA256    %d of %d match, %d MISMATCH" % (len(want) - len(bad), len(want), len(bad)))
    for b in bad[:10]:
        print("        MISMATCH %s" % b)

    exes = [(rel, p) for rel, p in have.items() if rel.lower().endswith(".exe")]
    foreign = []
    norm1 = []
    for rel, p in sorted(exes):
        blob = open(p, "rb").read()
        found = set(m.decode() for m in HEX40.findall(blob))
        # A 40-char hex RUN is not automatically a commit.  MEASURED on this package: every
        # binary contains forty ASCII '3' characters (filler/padding), which the bare regex
        # reports as a foreign commit.  A real SHA-1 has high digit variety; require at least
        # six distinct characters so the check flags provenance, not padding.
        others = {h for h in found - {RT1} if len(set(h)) >= 6}
        if RT1 not in found:
            norm1.append(rel)
        if others:
            foreign.append((rel, sorted(others)[:3]))
    print("  [3] COMMIT    %d .exe scanned; %d missing the rt1 commit; %d carrying a FOREIGN commit"
          % (len(exes), len(norm1), len(foreign)))
    for rel in norm1:
        print("        NO rt1 COMMIT  %s" % rel)
    for rel, o in foreign:
        print("        FOREIGN %s -> %s" % (rel, ", ".join(o)))

    ok = not (missing or extra or bad or norm1 or foreign)
    print("\n  VERDICT: %s" % ("PASS -- manifest, hashes and commit exclusivity all hold"
                               if ok else "FAIL"))
    sys.exit(0 if ok else 1)
