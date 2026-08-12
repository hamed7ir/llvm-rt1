#!/bin/bash
# rt1 --- A/B IDENTITY ARM.  Working rule 13.
#
# Every A/B harness in this project must prove it is actually running TWO DIFFERENT
# compilers before it measures anything, and every single-compiler harness must prove
# it is running the ONE it requires.
#
# WHY THIS EXISTS (MEASURED, 2026-08-05):
#   The Bug-4 upstream draft shipped a negative control labelled "stock 18.1.8" that had
#   in fact been run with the PATCHED compiler.  No instrument noticed.  It was caught
#   only because a reviewer spotted that the objects differed by a constant +188 bytes
#   --- the longer `Varan clang version 18.1.8-rt1 (...)` producer string, stored twice
#   in the debug info.  An A/B that cannot tell its own two arms apart is gate-vacuity
#   with both hands.
#
# USAGE
#   . "$(dirname "$0")/../tools/ab_arm.sh"
#   ab_arm_two  "$STOCK" "$RT1"          # A/B: the two must DIFFER
#   ab_arm_is   "$CC" --not rt1          # single-compiler: must NOT be the patched one
#   ab_arm_is   "$CC" --has rt1          # single-compiler: must BE the patched one
#
# All functions exit non-zero and print to stderr on violation.  They are meant to abort
# the harness, not to be advisory.

ab_arm_version() {
    # Print the first line of <compiler> --version, or fail loudly.
    local exe="$1"
    local v
    v="$(MSYS2_ARG_CONV_EXCL='*' "$exe" --version 2>/dev/null | head -1)"
    if [ -z "$v" ]; then
        echo "ab_arm: FATAL: '$exe' produced no --version output" >&2
        return 1
    fi
    printf '%s\n' "$v"
}

ab_arm_two() {
    # Assert two compilers are genuinely different builds.
    local a="$1" b="$2" va vb
    va="$(ab_arm_version "$a")" || return 1
    vb="$(ab_arm_version "$b")" || return 1
    if [ "$va" = "$vb" ]; then
        {
            echo "ab_arm: FATAL: A/B ARMS ARE THE SAME COMPILER --- refusing to measure."
            echo "  A: $a"
            echo "  B: $b"
            echo "  both report: $va"
            echo "  (working rule 13; this is the Bug-4 near-miss made impossible)"
        } >&2
        return 1
    fi
    echo "ab_arm: OK  A = $va"
    echo "ab_arm: OK  B = $vb"
    return 0
}

ab_arm_is() {
    # Assert a single compiler is / is not the one required.
    local exe="$1" mode="$2" needle="$3" v
    v="$(ab_arm_version "$exe")" || return 1
    case "$mode" in
      --has)
        case "$v" in
          *"$needle"*) echo "ab_arm: OK  $v"; return 0 ;;
          *) echo "ab_arm: FATAL: expected a compiler containing '$needle'; got: $v" >&2; return 1 ;;
        esac ;;
      --not)
        case "$v" in
          *"$needle"*) echo "ab_arm: FATAL: compiler must NOT contain '$needle'; got: $v" >&2; return 1 ;;
          *) echo "ab_arm: OK  $v"; return 0 ;;
        esac ;;
      *) echo "ab_arm: usage: ab_arm_is <exe> --has|--not <substring>" >&2; return 2 ;;
    esac
}

# Self-test: `bash tools/ab_arm.sh --self-test`
# Required to demonstrate the arm CAN fail, not merely that it can pass (rule 3).
if [ "${1:-}" = "--self-test" ]; then
    STOCK="/c/Program Files/LLVM/bin/clang.exe"
    RT1="/d/repo/llvm-rt/build/bin/clang.exe"
    rc=0
    echo "=== 1. two genuinely different compilers -> must PASS ==="
    ab_arm_two "$STOCK" "$RT1" || { echo "SELF-TEST FAIL: real A/B was rejected"; rc=1; }
    echo
    echo "=== 2. THE ARMED FLOOR: same compiler on both arms -> must FAIL ==="
    if ab_arm_two "$STOCK" "$STOCK" 2>/dev/null; then
        echo "SELF-TEST FAIL: identical arms were ACCEPTED (gate-vacuity)"; rc=1
    else
        echo "  correctly rejected"
    fi
    echo
    echo "=== 3. rt1 must be rejected where stock is required -> must FAIL ==="
    if ab_arm_is "$RT1" --not rt1 2>/dev/null; then
        echo "SELF-TEST FAIL: patched compiler accepted where stock required"; rc=1
    else
        echo "  correctly rejected"
    fi
    echo
    echo "=== 4. stock accepted where stock is required -> must PASS ==="
    ab_arm_is "$STOCK" --not rt1 || { echo "SELF-TEST FAIL: stock rejected"; rc=1; }
    echo
    [ $rc -eq 0 ] && echo "SELF-TEST: PASS (both directions demonstrated)" || echo "SELF-TEST: FAIL"
    exit $rc
fi
