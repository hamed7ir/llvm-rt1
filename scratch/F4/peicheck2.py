import re,sys
txt=open(sys.argv[1],errors='replace').read().splitlines()
fi={}
for L in txt:
    m=re.match(r'\s*fi#(-?\d+): (size=(\d+)|variable sized), align=\d+, at location \[SP([+-]\d+)\]',L)
    if m: fi[int(m.group(1))]=(m.group(3), int(m.group(4)))
# prologue: push {r4-r10}=28, push {r11,lr}=8  -> r11 = SPin-36 ; sub sp,#0x154 -> r6 = SPin-376
R11=-36; R6=int(sys.argv[2])
print("frame objects:",len(fi))
rows=[]
for L in txt:
    m=re.search(r'\$(r6|r11|sp), (-?\d+),.*%stack\.(\d+)',L)
    if not m: continue
    reg,off,idx=m.group(1),int(m.group(2)),int(m.group(3))
    if idx not in fi: continue
    size,loc=fi[idx]
    base={'r6':R6,'r11':R11}.get(reg)
    if base is None: continue
    resolved=base+off              # address relative to SPin
    err=resolved-loc               # 0 == correct
    rows.append((reg,idx,size,loc,off,resolved,err))
seen=set(); print(f"{'base':5} {'fi#':>4} {'size':>5} {'declared':>9} {'imm':>6} {'resolved':>9} {'ERROR':>6}")
for r in rows:
    k=(r[0],r[1])
    if k in seen: continue
    seen.add(k)
    print(f"{r[0]:5} {r[1]:4} {str(r[2]):>5} SP{r[3]:+6} {r[4]:6} SP{r[5]:+6} {r[6]:+6}")
import collections
c=collections.Counter((r[0],r[6]) for r in rows)
print("\n(base, error) histogram over ALL annotated refs:", dict(c))
