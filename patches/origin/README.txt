patches/origin/: every rt2.3 change on its own

The toolchain was BUILT from ../rt23-vs-23.1.1.patch. That's one file, the full diff from clean
llvmorg-23.1.1 (git diff --binary). Applied to a clean 23.1.1 it gives the same tree, file for file.
The files here are the same changes one at a time, so you can read them. RELEASE-NOTES.md has a
line on what each patch fixes.

There are four groups. Only the second, the third and the fourth apply as they are.

0002 0003 0004 0005 0007 0010: THE ORIGINAL rt1 PATCHES, written for LLVM 18.1.8.
  They are here because they explain the bugs: what was wrong, how it was measured, and why the
  fix looks the way it does. They are NOT exactly what rt2.3 was built from:

  0004  moved to new anchors. 23.x calls the parameter Reg instead of RegNum and uses Reg.id(),
        so the 18.x hunks don't apply.
  0007  THREE of its four hunks are left out on purpose. They pass an isMustTail parameter
        through IsEligibleForTailCallOptimization. 23.1.1 passes CallLoweringInfo into that
        function instead, so there is nothing to pass through. The hunk that stays is also
        tighter (byval arguments don't add to the save area).

  Don't run these patches' own lit tests against rt2.3 and expect them to pass. They test 18.x
  behaviour. 0007's test as rt2 shipped it had exactly that problem, see 0019.

0011 to 0020: rt2.1's, WRITTEN FOR 23.1.1. They apply as they are, each on top of 23.1.1 plus the
  patches before it. 0003, 0005, 0007, 0010 and 0011 start with a real explanation, 0002 and 0004
  are plain diffs, and 0012 to 0020 start with a one-line title and a note naming the script that
  generated them (that script is in my private working repo, not here). The codes in the titles
  (B2 to B7, V1) are my own bug numbers. rt2.1 applied them in this order: 0012 to 0016, 0018,
  0019, 0017, 0020, and number order gives the same tree too. Both orders were checked when rt2.1
  was built.

0021 to 0026 and B01 to B08: NEW IN rt2.2, git format-patch files, in this order on top of rt2.1:

  0021  lld COFF: LTO uses the static reloc model for ARMNT
  0022  lld COFF: ARM delay-load tail merge calls the helper by absolute address
  0023  llvm-lib: Triple::thumb maps to ARMNT for bitcode
  0024  CGProfile: no edges to intrinsics
  0025  lld COFF: deterministic call-graph sort
  0026  ARM MC: diagnose T32 STR with Rt = pc
  B01   [ARM] Fix miscompile in MAC for 64b values (#231702)
  B02   [ARM] Invalidate LiveRegPos when erasing current position (#226937)
  B03   [DAGCombiner] Require a 0/1 carry-in when rebuilding a borrow chain (#223396)
  B04   [DAGCombiner] Restrict combineOrOfSetCCToUSUBOCarry to ZeroOrOneBooleanContent (#224759)
  B05   [SelectionDAG] Do not flag undef bitcast lanes as known zero
  B06   [InstCombine] Fix miscompilation in sinkNotIntoOtherHandOfLogicalOp (#226783)
  B07   [GlobalsAA] Handle self-referencing stores in AnalyzeUsesOfPointer (#213631)
  B08   [SimplifyLibCalls] Fix ConstantInt construction based on char (#231159)

  Each one applied to the tree before it gives that commit's tree, and all 14 in order on top of
  rt2.1 give the tree rt2.2 was built from. Apply the B patches with git am --keep-non-patch, or
  git drops their [ARM]-style subject tags. B01 to B08 keep their upstream authors and messages.
  B02 did not apply to 23.1.1 as upstream wrote it, because the code after one of its hunks is
  older here. It went in with two lines of context on each side, and a note in its message says
  so. Its own changed lines are upstream's.

0027 and 0028: NEW IN rt2.3, git format-patch files, in this order on top of rt2.2:

  0027  clang MS ABI: image-relative C++ throw information on 32-bit Arm
  0028  clang: __ARM_SIZEOF_WCHAR_T is the size of the target's wchar_t

  Each one applied to the tree before it gives that commit's tree, and both in order on top of
  rt2.2 give the tree rt2.3 was built from.
