patches/origin/: every rt2.1 change on its own

The toolchain was BUILT from ../rt21-vs-23.1.1.patch. That's one file, the full diff from clean
llvmorg-23.1.1, made from the two source trees and checked by applying it to a fresh 23.1.1 and
comparing file for file. The files here are the same changes one at a time, so you can read them.
0003, 0005, 0007, 0010 and 0011 start with a real explanation. 0002 and 0004 are plain diffs.
0012 to 0020 start with a one-line title and a note naming the script that generated them; that
script and its notes are in my private working repo, not here. The codes in the titles (B2 to B7,
V1) are my own bug numbers. RELEASE-NOTES.md has a line on what each patch fixes.

There are two groups, and only the second one applies as it is.

0002 0003 0004 0005 0007 0010: THE ORIGINAL rt1 PATCHES, written for LLVM 18.1.8.
  They are here because they explain the bugs: what was wrong, how it was measured, and why the
  fix looks the way it does. They are NOT exactly what rt2.1 was built from:

  0004  moved to new anchors. 23.x calls the parameter Reg instead of RegNum and uses Reg.id(),
        so the 18.x hunks don't apply.
  0007  THREE of its four hunks are left out of rt2.1 on purpose. They pass an isMustTail
        parameter through IsEligibleForTailCallOptimization. 23.1.1 passes CallLoweringInfo into
        that function instead, so there is nothing to pass through. The hunk that stays is also
        tighter (byval arguments don't add to the save area).

  Don't run these patches' own lit tests against rt2.1 and expect them to pass. They test 18.x
  behaviour. 0007's test as rt2 shipped it had exactly that problem, see 0019.

0011 to 0020: WRITTEN FOR 23.1.1, in the order they were applied. They apply as they are (each on
  top of 23.1.1 plus the patches before it), and their tests pass on rt2.1:

  0011  _ReadWriteBarrier, _ReadBarrier, _WriteBarrier built in on 32-bit Arm
  0012  MSVC ARM intrinsics, and _AddressOfReturnAddress
  0013  lifetime_capture_by deprecation warning off by default
  0014  pcs("aapcs-vfp") accepted on Windows on Arm
  0015  lld range-extension thunk margins
  0016  @feat.00 on ARM COFF objects
  0017  C++ exceptions on Windows ARM32
  0018  lld BRANCH20T J1/J2 bits
  0019  0007's test updated for LLVM 23
  0020  _AddressOfReturnAddress stack slot (finishes 0012)

  They were applied in this order: 0012 to 0016, 0018, 0019, 0017, 0020. Each file is only that
  patch's own change, and applying them in NUMBER order on top of rt2 plus 0011 gives the same
  tree too.
  Both orders were checked when the package was built.
