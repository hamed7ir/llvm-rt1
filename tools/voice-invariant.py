"""Voice-pass invariant checker.

A voice pass may rewrite prose freely but must not touch facts. This extracts every FACTUAL
TOKEN from a document -- numbers, hex digests, paths, flags, commands, filenames -- and compares
two snapshots as multisets.

The pass condition is asymmetric on purpose:

    ADDED tokens      -> ALWAYS a failure. A voice pass invents nothing.
    CHANGED tokens    -> ALWAYS a failure (shows up as one add + one remove).
    REMOVED tokens    -> allowed ONLY inside spans the batch sanctioned for deletion
                         (T2 tool-output transcripts, T3 internal-question paragraphs).
                         Every removal is listed so it can be judged one by one.

Usage:
    python tools/voice-invariant.py snap  <file> <out.json>
    python tools/voice-invariant.py check <file> <before.json>
"""
import io, json, re, sys, collections

sys.stdout.reconfigure(encoding="utf-8")

PATTERNS = [
    ("hex",     r"\b[0-9a-f]{8,64}\b"),                       # sha256 / commit hashes
    ("num",     r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])"),     # 252, 1,239, 18.1.8 parts
    ("flag",    r"(?<![\w/])(?:--?[A-Za-z][\w-]*(?:=[\w./-]+)?|/[A-Z][A-Za-z]*)\b"),
    ("path",    r"[\w.\-]+(?:[/\\][\w.\-]+)+"),               # repo paths, DLLs, headers
    ("file",    r"\b[\w.\-]+\.(?:cpp|h|py|sh|bat|ll|mir|md|txt|exe|dll|json|test|obj|log|s|td|cmake|inc|yaml)\b"),
]

def tokens(text):
    bag = collections.Counter()
    for name, pat in PATTERNS:
        for m in re.finditer(pat, text):
            bag[(name, m.group(0))] += 1
    return bag

def load(p):
    return io.open(p, encoding="utf-8", errors="replace").read()

mode = sys.argv[1]
if mode == "snap":
    bag = tokens(load(sys.argv[2]))
    io.open(sys.argv[3], "w", encoding="utf-8").write(
        json.dumps({"%s\t%s" % k: v for k, v in bag.items()}, indent=0))
    print("  snapshot: %d distinct factual tokens, %d occurrences  <- %s"
          % (len(bag), sum(bag.values()), sys.argv[2]))

elif mode == "check":
    now = tokens(load(sys.argv[2]))
    raw = json.loads(io.open(sys.argv[3], encoding="utf-8").read())
    before = collections.Counter({tuple(k.split("\t", 1)): v for k, v in raw.items()})

    added   = {k: now[k] - before.get(k, 0) for k in now if now[k] > before.get(k, 0)}
    removed = {k: before[k] - now.get(k, 0) for k in before if before[k] > now.get(k, 0)}

    print("  before: %d distinct / %d occurrences" % (len(before), sum(before.values())))
    print("  after : %d distinct / %d occurrences" % (len(now), sum(now.values())))

    print("\n  ADDED (must be EMPTY -- a voice pass invents nothing):")
    if not added:
        print("    none")
    for (kind, tok), n in sorted(added.items()):
        print("    +%-3d %-5s %s" % (n, kind, tok))

    print("\n  REMOVED (each must sit inside a sanctioned deletion -- judge one by one):")
    if not removed:
        print("    none")
    for (kind, tok), n in sorted(removed.items()):
        print("    -%-3d %-5s %s" % (n, kind, tok))

    print("\n  VERDICT: %s" % ("FAIL -- tokens added or altered" if added
                               else "pass on the add-side; %d removal(s) to justify" % len(removed)))
    sys.exit(1 if added else 0)
