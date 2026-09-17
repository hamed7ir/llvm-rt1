THESE ARE NOT THE PATCHES rt2 WAS BUILT FROM.

The six diffs in this directory are the ORIGINAL rt1 patches, written against LLVM 18.1.8.
They are here because they carry the defect analysis -- what was wrong, how it was measured,
and why the fix is shaped the way it is. That reasoning is worth reading and does not change.

What rt2 was actually built from is ../rt2-vs-23.1.1.patch, one file, generated from the two
source trees and verified by applying it to a fresh llvmorg-23.1.1 and comparing the result to
rt2's source byte for byte.

They differ, and not trivially:

  0004  re-anchored. 23.x spells the parameter Reg rather than RegNum and uses Reg.id(),
        so the 18.x hunks do not apply.

  0007  THREE of its four hunks are deliberately ABSENT from rt2. They thread an isMustTail
        parameter through IsEligibleForTailCallOptimization; 23.1.1 passes CallLoweringInfo
        into that function instead, so CLI.CB is already in scope and there is nothing to
        thread. The surviving hunk is also tightened: the exemption fires only when the
        argument-register save area has no byval contribution, because 23 grew a separate
        byval tail-call path (ByValNeedsCopyForTailCall) that 18.x did not have.

⚠ DO NOT run these patches' lit tests against rt2 and expect them to pass. 0007's tests encode
18.x behaviour, and LLVM 23 legitimately differs: it tail-calls two shapes 0007 keeps as
ordinary calls, with no rt1 patch applied at all. That is upstream behaviour rt2 inherits, not
a defect rt2 introduced -- and it is an open question, documented in RELEASE-NOTES.md, because
nobody has executed it.
