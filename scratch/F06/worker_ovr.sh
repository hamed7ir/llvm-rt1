#!/bin/bash
# F0.6 layout audit - STEP 2 worker: re-run ONE production compile command under
# clang 21 with -Wpadded-bitfield and -fdump-record-layouts-complete (which forces
# layout of EVERY complete record decl, not just the ones the TU happens to use).
# stdin: "DIR<TAB>clang-cl.EXE ...args... source.cpp"
# stdout: TSV status line;  padding diags appended to $HITS
C21="${AUDIT_CC:-/d/repo/llvm-rt/clang21/pkg/bin/clang-cl.exe}"
HITS="${HITS:-/d/repo/llvm-rt/scratch/F06/hits.txt}"
export MSYS2_ARG_CONV_EXCL='*'
export INCLUDE='D:\Program Files\Vscom\VC\Tools\MSVC\14.16.27023\include;D:\Windows Kits\10\Include\10.0.19041.0\ucrt;D:\Windows Kits\10\Include\10.0.19041.0\um;D:\Windows Kits\10\Include\10.0.19041.0\shared;D:\Windows Kits\10\Include\10.0.19041.0\winrt'

# --- IDENTITY ARM (working rule 13) -----------------------------------------
# This is the OVERRIDE worker -- the rt1 arm of the T1 layout oracle.  Line 7 falls
# back to /d/repo/llvm-rt/clang21/pkg/bin/clang-cl.exe, which is the SAME clang 21
# that produced the banked baseline hits-pass1.txt (1355 hits).  So if AUDIT_CC is
# unset, not exported past `xargs`, or misspelled, all 2,582 TUs are compiled by the
# BASELINE compiler and logs/f06-oracle-rt1.log prints
#   baseline 1355 / rt1+0006 1355 / differing 0 / FINDING-FOR-FINDING AGREEMENT
# -- a verdict byte-identical to a real pass, which is in fact clang 21 agreeing with
# itself.  That is the Bug-4 near-miss with the two arms not swapped but IDENTICAL,
# and nothing downstream of here can tell the difference.
#
# Therefore: (a) an unset AUDIT_CC is refused outright -- there is no legitimate use
# of THIS script without one (that job belongs to worker.sh, which hardcodes clang 21);
# (b) any AUDIT_CC whose --version equals the baseline's is refused by ab_arm_two.
# The one real baseline-arm use is a DIRECT single-TU invocation of this worker as a
# reference measurement -- T9a/RECON-dumpflag-crash.md 6.2 step 2, banked as the
# one-line st3-CLANG21.tsv (rc=0, records=1660) beside st3-RT1_PRE0006.tsv /
# st3-RT1_0006.tsv.  That use survives, but must now say AUDIT_ALLOW_BASELINE=1, which
# announces itself on stderr so the result cannot be filed as an A/B agreement.
# (sweep_ovr.sh has its own, stricter arm: it refuses the fallback compiler outright
# and sends whole-sweep reference runs to sweep.sh.  Both arms are wanted -- this one
# also covers `bash worker_ovr.sh "<line>"` with the driver bypassed entirely.)
#
# Cached in a stamp file, because this worker runs 2,582x under `xargs -P8` and the
# assertion costs two process spawns.  Unlike T3/interesting_rt1.sh's bare .armed
# sentinel, the stamp records WHICH compiler was armed (path + size + mtime + mode):
# AUDIT_CC changes from run to run here, so a contentless sentinel would let the very
# next (vacuous) sweep inherit the previous sweep's verdict.  sweep_ovr.sh clears the
# stamp and arms once up front via `bash worker_ovr.sh --arm`; this block additionally
# covers standalone `bash worker_ovr.sh "<line>"` invocations.
#
# exit 255, not 1: GNU xargs aborts the whole sweep immediately on 255 (MEASURED), so
# a mis-armed sweep dies on the first TU instead of emitting 2,582 refusals.
AB_ARM="/d/repo/llvm-rt/tools/ab_arm.sh"
BASELINE_CC="/d/repo/llvm-rt/clang21/pkg/bin/clang-cl.exe"
ARMSTAMP="${ARMSTAMP:-/d/repo/llvm-rt/scratch/F06/.armed-worker-ovr}"
armkey="$C21|$(stat -c '%s:%Y' "$C21" 2>/dev/null)|allow=${AUDIT_ALLOW_BASELINE:-0}"
if [ "$(cat "$ARMSTAMP" 2>/dev/null)" != "$armkey" ]; then
    if [ -z "${AUDIT_CC:-}" ]; then
        {
          echo "worker_ovr.sh: FATAL: AUDIT_CC is unset -- the audit compiler silently"
          echo "  defaulted to the BASELINE clang 21:"
          echo "    $BASELINE_CC"
          echo "  This sweep would recompile every TU with the compiler that PRODUCED"
          echo "  hits-pass1.txt and then report perfect agreement with it.  Refusing."
          echo "  Set AND EXPORT AUDIT_CC, e.g."
          echo "    AUDIT_CC=/d/repo/llvm-rt/build/bin/clang-cl.exe bash sweep_ovr.sh"
          echo "  (working rule 13)"
        } >&2
        exit 255
    fi
    . "$AB_ARM"
    armout="$(ab_arm_two "$C21" "$BASELINE_CC" 2>&1)"; armrc=$?
    if [ $armrc -ne 0 ]; then
        if [ "${AUDIT_ALLOW_BASELINE:-0}" = "1" ] && [ -n "$(ab_arm_version "$C21" 2>/dev/null)" ]; then
            {
              echo "worker_ovr.sh: NOTE: AUDIT_ALLOW_BASELINE=1 -- the audit arm IS the"
              echo "  baseline compiler.  This run is a REFERENCE arm, NOT an A/B result;"
              echo "  do not quote its agreement as evidence of anything.  (rule 13)"
            } >&2
        else
            printf '%s\n' "$armout" >&2
            {
              echo "worker_ovr.sh: FATAL: refusing to measure."
              echo "  AUDIT_CC = $C21"
              echo "  baseline = $BASELINE_CC"
              echo "  Deliberate baseline reference arm?  Re-run with AUDIT_ALLOW_BASELINE=1."
            } >&2
            exit 255
        fi
    fi
    printf '%s' "$armkey" > "${ARMSTAMP}.$$" && mv -f "${ARMSTAMP}.$$" "$ARMSTAMP"
fi
# Arm-only mode, used by sweep_ovr.sh to assert once before spawning 2,582 workers.
[ "$1" = "--arm" ] && { echo "worker_ovr.sh: ARMED  audit=$C21"; exit 0; }
# ----------------------------------------------------------------------------

line="$1"
dir="${line%%$'\t'*}"
cmd="${line#*$'\t'}"

# Strip: the driver name, -c, -Fo<x>, -Fd<x>, -Zi (no codegen wanted), -showIncludes.
args=$(printf '%s' "$cmd" \
  | sed -e 's#^clang-cl\.EXE ##' \
        -e 's#-Fo[^ ]*##g' -e 's#-Fd[^ ]*##g' \
        -e 's# -Zi # #g' \
        -e 's# -c # #')
src=$(printf '%s' "$args" | awk '{print $NF}')

cd "$dir" 2>/dev/null || { echo -e "${src}\tNODIR\t0\t0\t0"; exit 0; }

DUMP=""
[ -n "$DUMPALL" ] && DUMP="-Xclang -fdump-record-layouts-complete"
err=$(mktemp); out=$(mktemp)
eval "\"$C21\" $args -fsyntax-only -Wno-error -Wpadded-bitfield $DUMP" >"$out" 2>"$err"
rc=$?
nrec=$(grep -c 'Dumping AST Record Layout' "$out" 2>/dev/null)
nerr=$(grep -c ' error: ' "$err" 2>/dev/null)
nbf=$(grep -c 'Wpadded-bitfield' "$err" 2>/dev/null)
if [ "$nbf" -gt 0 ]; then
  grep 'Wpadded-bitfield' "$err" | sed "s#^#${src}\t#" >> "$HITS"
fi
if [ "$nerr" -gt 0 ]; then
  grep ' error: ' "$err" | head -2 | sed "s#^#${src}\tFIRSTERR\t#" >> "${HITS}.errs"
fi
echo -e "${src}\trc=${rc}\trecords=${nrec}\terrors=${nerr}\tbitfield=${nbf}"
rm -f "$err" "$out"
