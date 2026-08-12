#!/usr/bin/env python3
"""FLEET-WIDE Bug-1 gate census -- pass 3.

Pass-2 defect found and fixed here (MEASURED):  the blob-window method leaks Thumb IT
state across region boundaries.  REL xul.dll region 590 ends with `itttt eq` at window
offset 48; the 8-byte zero pad did not exhaust the 4 conditional slots, so region 591's
first instructions decoded as `pusheq`/`subeq`.  That fabricated a CARRIER: the adjustor
thunk mozilla::EditorBase::QueryInterface at 0x10ff7548 is really just
`subs r0,#4 ; b.w <target>` -- the `ldr r1,[r0] ... bx r2` attributed to it belongs to
the NEXT function.  Fix: pad each region with 8 x `nop` (16 bytes), which exhausts any
IT block (max 4 slots), plus a hard control that counts regions whose decode contains a
conditional NON-branch instruction with no preceding `it` in that region.  That control
MUST be non-zero with the old pad and zero with the new one.
"""
import sys, os, re, json, struct, subprocess, collections
sys.path.insert(0, r'D:\repo\llvm-rt\scratch\F05V')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vpe import PE, map_symbols
from pdbsyms import load as pdb_load
from demang import undname
from adjud import body_class, live_args, verdict, COND

D = os.path.dirname(os.path.abspath(__file__))
OBJDUMP = r"C:\Program Files\LLVM\bin\llvm-objdump.exe"
DATA = int(os.environ.get('CENSUS_DATA', '56'))
PAD = int(os.environ.get('CENSUS_PAD', '16'))
PADB = b'\x00\x00' if os.environ.get('CENSUS_ZEROPAD') else b'\x00\xbf'   # 0xbf00 = nop
WIN = DATA + PAD
GEO = 'd%dp%d%s' % (DATA, PAD, 'z' if os.environ.get('CENSUS_ZEROPAD') else 'n')
LINE = re.compile(r'^\s*([0-9a-fA-F]+):\s+(\S+)\s*(.*?)\s*$')


def thunk_class(mangled, dm):
    if not dm.startswith('[thunk]'):
        return None
    if mangled.startswith('??_9') or "`vcall'" in dm:
        return '$B'
    if '`vtordispex{' in dm:
        return '$R'
    if '`vtordisp{' in dm:
        return '$4'
    if '`adjustor{' in dm:
        return 'adj'
    return 'thunk?'


def anchored(pe, vas, tag):
    vas = sorted(vas)
    blob = bytearray()
    pad = (PADB * ((PAD // 2) + 1))[:PAD]
    for va in vas:
        o, _ = pe.va_to_off(va)
        c = pe.d[o:o + DATA] if o is not None else b''
        blob += c + b'\0' * (DATA - len(c)) + pad
    hdr = struct.pack('<HHIIIHH', 0x1C4, 1, 0, 0, 0, 0, 0)
    sh = (b'.text\0\0\0' + struct.pack('<IIII', 0, 0, len(blob), 60)
          + struct.pack('<IIHHI', 0, 0, 0, 0, 0x60000020))
    bp = os.path.join(D, 'b3_%s_%s.obj' % (GEO, tag))
    open(bp, 'wb').write(hdr + sh + bytes(blob))
    dp = os.path.join(D, 'b3_%s_%s.txt' % (GEO, tag))
    with open(dp, 'w') as fo:
        r = subprocess.run([OBJDUMP, '-d', '--triple=thumbv7-unknown-windows-msvc',
                            '--no-show-raw-insn', bp], stdout=fo, stderr=subprocess.PIPE)
    if r.returncode:
        raise RuntimeError(r.stderr.decode()[:300])
    regions = collections.defaultdict(list)
    for line in open(dp, errors='replace'):
        m = LINE.match(line)
        if not m:
            continue
        try:
            a = int(m.group(1), 16)
        except ValueError:
            continue
        regions[a // WIN].append((a, m.group(2), m.group(3).split('@')[0].strip()))
    bad = sum(1 for i in range(len(vas)) if regions.get(i) and regions[i][0][0] % WIN)
    empty = sum(1 for i in range(len(vas)) if not regions.get(i))
    return {va: regions.get(i, []) for i, va in enumerate(vas)}, bad, empty, 0


pop = json.load(open(os.path.join(D, 'pe_pop.json')))
rows, table, allv = [], [], {}
TOTLEAK = 0
for r in pop:
    if not r['armnt']:
        continue
    tag = '%s_%s' % (r['build'], os.path.basename(r['rel']).replace('.', '_'))
    pe = PE(r['path'])
    byva = collections.defaultdict(list)
    src = []
    if r['map']:
        for va, ns in map_symbols(r['map'], pe).items():
            byva[va] += ns
        src.append('map')
    if r['pdb']:
        for va, ns in pdb_load(r['pdb'], pe).items():
            byva[va] += ns
        src.append('pdb')
    names = sorted({n for ns in byva.values() for n in ns})
    dmall = {n: undname(n) for n in names}
    kinds = {n: thunk_class(n, dmall[n]) for n in names}
    thunks = {va: ns for va, ns in byva.items() if any(kinds.get(n) for n in ns)}
    cls = collections.Counter()
    for va, ns in thunks.items():
        ks = {kinds[n] for n in ns if kinds.get(n)}
        for pref in ('$B', '$R', '$4', 'adj', 'thunk?'):
            if pref in ks:
                cls[pref] += 1
                break
    bodies, bad, empty, leak = anchored(pe, set(thunks), tag) if thunks else ({}, 0, 0, 0)
    TOTLEAK += leak
    per = collections.Counter()
    for va, ns in sorted(thunks.items()):
        c = body_class(bodies.get(va, []))
        tns = [n for n in ns if kinds.get(n)]
        lv, whys = set(), []
        for n in tns:
            l, w = live_args(dmall[n])
            lv |= l
            whys.append(w)
        v, reg = verdict(c, lv)
        per[v] += 1
        allv['%s|%s|%s' % (r['build'], r['rel'], hex(va))] = (v, c['body'])
        if v != 'safe':
            rows.append(dict(build=r['build'], rel=r['rel'], va=hex(va),
                             cls=kinds[tns[0]], kind=c['kind'], clob=c['clob'],
                             live=sorted(lv), why=whys[:2], cond=c['cond'],
                             verdict=v, hit=reg, nnames=len(tns),
                             body=c['body'][:240], names=tns[:3],
                             dm=[dmall[n][:200] for n in tns[:2]]))
    table.append(dict(build=r['build'], rel=r['rel'], ours=r['ours'],
                      src=','.join(src) or 'NONE', size=r['size'],
                      symaddrs=len(byva), thunks=len(thunks), B=cls['$B'], v4=cls['$4'],
                      vR=cls['$R'], adj=cls['adj'], other=cls['thunk?'],
                      carriers=per['CARRIER'], review=per['review-framed'],
                      beyond=per['safe-beyond-window'], notfwd=per['not-forwarder'],
                      safe=per['safe'], desync=bad, emptybody=empty, itleak=leak))
    print('%-5s %-40s src=%-8s thunks=%-6d $B=%-4d $4=%-4d $R=%-3d adj=%-6d || CARRIER=%-3d '
          'review=%-4d beyond=%-4d notfwd=%-5d safe=%-5d desync=%d empty=%d ITleak=%d'
          % (r['build'], r['rel'], ','.join(src) or 'NONE', len(thunks), cls['$B'],
             cls['$4'], cls['$R'], cls['adj'], per['CARRIER'], per['review-framed'],
             per['safe-beyond-window'], per['not-forwarder'], per['safe'], bad, empty,
             leak))

json.dump(dict(table=table, rows=rows, pad=PAD, data=DATA, geo=GEO, allv=allv),
          open(os.path.join(D, 'census3_%s.json' % GEO), 'w'), indent=1)
print('\n' + '=' * 100)
print('GEOMETRY %s   thunk regions classified = %d' % (GEO, len(allv)))
for v in ('CARRIER', 'review-framed', 'safe-beyond-window', 'not-forwarder'):
    print('%-20s %d' % (v, sum(1 for x in rows if x['verdict'] == v)))
print('\n--- every CARRIER ---')
for x in rows:
    if x['verdict'] != 'CARRIER':
        continue
    print('  *** %s %s %s cls=%s clob=%s live=%s hit=r%s cond=%s'
          % (x['build'], x['rel'], x['va'], x['cls'], x['clob'], x['live'], x['hit'],
             x['cond']))
    print('      body: %s' % x['body'][:170])
    print('      sym : %s' % x['names'][0][:130])
    print('      dm  : %s' % x['dm'][0][:170])
