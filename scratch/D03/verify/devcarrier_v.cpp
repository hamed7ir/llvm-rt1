// ADVERSARIAL VERIFICATION of FLEET-d03.md section 5.5.
//
// FLEET-d03 claims the DEV carrier (FLEET-CENSUS.md:316)
//     10ec0e00: e9dd 1300  ldrd r1, r3, [sp]
//     10ec0e04: 38d8       subs r0, #0xd8
//     10ec0e06: e9cd 1300  strd r1, r3, [sp]
//     10ec0e0a: f7ff bfd2  b.w  <PresShell::ContentStateChanged>
// is explained by callee-liveness IPO.  But its own repro (devcarrier.cpp) emitted
//     ldrd r0, r1, [sp]   (USE_ADOC=0)  /  ldrd r0, r2, [sp]  (USE_ADOC=1)
// and never the observed r1,r3 pair, and never the `subs r0` -- because in that file
// the callee ignores `this` too, so r0 was dead and the this-adjust was folded away.
// So section 5.5's final paragraph is an EXTRAPOLATION, not a reproduction.
//
// This file supplies the missing liveness profile of the REAL callee, read off the
// disassembly quoted in FLEET-CENSUS.md:330-337 and FLEET-d03.md section 5.5:
//     r0 (this)      LIVE   -- callee does `mov r4,r0 ; ldrb.w r0,[r0,#0xab]`
//     r1 (aDocument) DEAD   -- NS_PRECONDITION only; callee first WRITES r1
//     r2 (aContent)  LIVE   -- callee does `mov r5,r2`
//     r3             AAPCS 8-byte alignment padding, dead by ABI
// PREDICTION under FLEET-d03's mechanism: scratch = the two dead core registers r1 and
// r3, and the this-adjust survives  ->  e9dd 1300 / 38d8 / e9cd 1300 / b.w
//
// MODE selects the callee's liveness:
//   0 : reads aContent only                  (r0 dead, r1 dead, r2 live)  [FLEET's arm]
//   1 : reads aDocument only                 (r0 dead, r1 live, r2 dead)  [FLEET's control]
//   2 : reads this + aContent, NOT aDocument (r0 live, r1 DEAD, r2 live)  [the REAL callee]
//   3 : reads this + aDocument + aContent    (r0,r1,r2 all live)          [must-fail control]
struct nsIDocument;
struct nsIContent;
struct EventStates { unsigned long long mStates; };

#ifndef MODE
#define MODE 2
#endif

struct IDocObserver {
  virtual void ContentStateChanged(nsIDocument *, nsIContent *, EventStates);
};
struct IFiller { virtual void filler(); char pad[208]; };
struct IOther {
  virtual void ContentStateChanged(nsIDocument *, nsIContent *, EventStates);
};
struct PresShell : IDocObserver, IFiller, IOther {
  void filler() override;
  void ContentStateChanged(nsIDocument *, nsIContent *, EventStates) override;
  unsigned char mPaintingSuppressed;
};

extern void sink(void *, unsigned long long);
extern void sink2(void *, void *, unsigned long long);

__declspec(noinline) void PresShell::ContentStateChanged(nsIDocument *aDocument,
                                                         nsIContent *aContent,
                                                         EventStates aStateMask) {
#if MODE == 0
  sink(aContent, aStateMask.mStates);
#elif MODE == 1
  sink(aDocument, aStateMask.mStates);
#elif MODE == 2
  if (mPaintingSuppressed)                       // reads `this`  -> r0 LIVE
    sink(aContent, aStateMask.mStates);          // reads aContent -> r2 LIVE
#elif MODE == 3
  if (mPaintingSuppressed)
    sink2(aDocument, aContent, aStateMask.mStates);
#endif
}
void PresShell::filler() { sink(this, 0); }
PresShell *make() { return new PresShell(); }
