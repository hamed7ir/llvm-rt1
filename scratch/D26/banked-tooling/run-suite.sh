#!/bin/sh
# ============================================================================
# Varan  INTERWORKING SUITE  (standing, FAIL-LOUD)  --  run-suite.sh
# ----------------------------------------------------------------------------
# Varan (M3). Run ONCE PER BUILD WAVE, after `mach build`, in the
# MozillaBuild shell. Applies the two DEVICE-PROVEN systemic clang-cl/lld thumbv7
# ARM fixers, then runs ALL FOUR standing gates over EVERY our-built dist/bin PE,
# self-enumerating. If ANY gate does not pass, the suite EXITS NONZERO (fail-loud)
# -- this is what makes fast batched fixing safe on hardware that fails silently.
#
# THE CODE-POINTER-INTEGRITY FAMILY this suite defends (see SUITE.md):
#   Fixer 1  vcall-thunk r12 override   (clang emits ??_9 $B thunks using r1=arg1)
#   Fixer 2  __imp_ Thumb-bit fix       (lld auto-import to a folded Thumb fn -> even ptr)
#   Gate  poison   (ARMNT 0x1C4)        Gate  dialect  (Thumb-2 only, no A32)
#   Gate  thunk-r12                     Gate  __imp_ Thumb-bit
#
# The fixer IMPLEMENTATIONS live in their device-proven homes (varan-thunk-override/
# + repo-root gates); this suite is the standing ORCHESTRATOR + coverage + fail-loud.
# Prebuilt third-party PEs (no objdir .pdb, e.g. d3dcompiler_47.dll, the x86 uninstall
# helper) are NEVER touched or gated -- scoped to binaries WE compiled via is_ours().
# ============================================================================
set -e
ROOT=/d/repo/mozbuild
OBJ=$ROOT/palemoon/obj-browser-arm32
BIN=$OBJ/dist/bin
GT=$ROOT/varan-thunk-override
READOBJ="/c/Program Files/LLVM/bin/llvm-readobj"

is_ours() {  # $1 = PE path; true if we built it (has an objdir .pdb)
  n=$(basename "$1"); n="${n%.*}"
  [ -n "$(find "$OBJ" -name "$n.pdb" 2>/dev/null | head -1)" ]
}
ours_pes() { for f in $(find "$BIN" \( -name '*.dll' -o -name '*.exe' \) 2>/dev/null); do [ -f "$f" ] && is_ours "$f" && printf '%s\n' "$f"; done; }  # RECURSIVE (M4.1b Task 2): dist/bin/** incl browser/components/browsercomps.dll

echo "############ varan-interwork: FIXERS ############"
echo "== [FIX 1/2] vcall-thunk r12 override: relink \$B-thunk carriers via the wrapper =="
sh "$GT/relink-with-override.sh"                       # regen override obj + relink + copy to dist/bin
echo "== [FIX 2/2] __imp_ Thumb-bit fix: our-built PEs only =="
ours_pes | while read -r f; do python3 "$GT/varan-imp-fix.py" "$f"; done

echo "############ varan-interwork: STANDING GATES (fail-loud) ############"
rc=0

echo "== [GATE 1/5] poison: every our-built dist/bin PE is ARMNT (0x1C4) =="
n=0; bad=0
for f in $(ours_pes); do
  n=$((n+1))
  m=$("$READOBJ" --file-headers "$f" 2>/dev/null | grep -i 'Machine:' | head -1 | sed 's/^ *//')
  case "$m" in *ARMNT*|*0x1C4*) : ;; *) echo "   POISON FAIL: $(basename "$f")  $m"; bad=$((bad+1));; esac
done
[ "$bad" -eq 0 ] && echo "   poison PASS: $n/$n our-built PEs ARMNT" || rc=1

echo "== [GATE 2/5] dialect: Thumb-2 only (no .arm/.code 32) =="
sh "$ROOT/a32-dialect-gate.sh" "$OBJ" || rc=1

echo "== [GATE 3/5] thunk-r12: every ??_9 \$B vcall thunk uses r12 (arg1 preserved) =="
python3 "$GT/gate-thunks.py" "$OBJ" --expect-min 178 --class-floors B=44,4=73,R=0,adj=4217 --expect-pes 19 --max-review 844 || rc=1  # H1 (VARAN-ACCEPT-1 2026-08-09): the $4/$R/adjustor families are now ARMED TOO. Floors are ADDRESS-level from the vendored census (varan-thunk-override/census/), which reproduces FLEET-CENSUS.md exactly: $B 44, $4 73, $R EXACTLY 0 (a floor of 0 is vacuous, so it is asserted equal, not >=), adjustor 4217, over 19 our-built ARMNT PEs; review-framed ceiling 844 = its measured clean-fleet baseline, because "not adjudicated" must never score as "safe". NOTE --expect-min 178 is NAME-level from the two linker maps and is a DIFFERENT basis from $B=44 (ICF folds 176 names onto 44 addresses) -- both are kept because they fail on different regressions. All four floors demonstrated firing.   # F0.2: ARM the shrinking-denominator floor (census 178 = xul.dll 176 + libGLESv2.dll 2). Unarmed the floor defaulted to 1, so 178->1 still printed PASS (gate-vacuity #11). NOT armed in selftest.sh: its fixture is xul-only = 176.

echo "== [GATE 4/5] __imp_: no local .text function pointer is even (missing Thumb bit) =="
for f in $(ours_pes); do python3 "$GT/varan-imp-fix.py" "$f" --gate || rc=1; done

echo "== [GATE 5/5] jit-obj: poison + dialect + bug#5 screen over the JIT's own objects =="
# Varan JIT device enablement (2026-07-22). The JIT backend's own C++ is compiled by the same
# clang-cl thumbv7 as everything else, so it is subject to bugs #1/#2/#5 like any other object
# -- and until now NO jit object was gated at all. Skipped (not failed) when the objdir has no
# jit/arm objects, so this suite still runs unchanged against a browser build that predates the
# JIT, rather than turning "not applicable" into a red gate.
JITOBJ="$OBJ/js/src/jit"
if [ -d "$JITOBJ" ] && [ -n "$(find "$JITOBJ" -name '*.obj' -print -quit 2>/dev/null)" ]; then
  sh "/d/repo/mozbuild/varan-jit/tools/jit-obj-gate.sh" "$JITOBJ" || rc=1
else
  echo "   skip: no JIT objects under $JITOBJ (pre-JIT build)"
fi

if [ "$rc" -eq 0 ]; then
  echo "############ varan-interwork: ALL FIXERS APPLIED + ALL 5 GATES PASS ############"
else
  echo "############ varan-interwork: GATE FAILURE -- BUILD IS NOT DEVICE-SAFE ############" >&2
fi
exit $rc
