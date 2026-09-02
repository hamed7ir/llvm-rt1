aeabi-shim.c -- WHEN YOU NEED IT, AND WHEN YOU DO NOT
=====================================================

rt1.1 ships no compiler-rt builtins archive. There is no clang_rt.builtins-*.lib for a
Windows thumb triple in this package, and that is a decision, not an omission (see D15 in
DISPOSITION-TABLE.md). This file is the mitigation, shipped so that porters can obtain it.


YOU ALMOST CERTAINLY DO NOT NEED IT
-----------------------------------

Ordinary C and C++ integer division on this target does NOT ask for the EABI helpers.

  MEASURED 2026-08-31, rt1.1 clang-cl, --target=thumbv7-unknown-windows-msvc -O1, on

      int      d(int a, int b)           { return a / b; }
      unsigned u(unsigned a, unsigned b) { return a % b; }

  the only undefined symbols in the object are:

      U __rt_sdiv
      U __rt_udiv

  Those are MSVC ARM CRT entry points and the CRT ships them. No __aeabi_* symbol appears.

So compiler-generated code never needs this shim. Linking a normal C/C++ project against the
MSVC 14.16 ARM CRT works with the shim ABSENT.


YOU NEED IT ONLY IF YOUR SOURCE NAMES THE SYMBOLS
-------------------------------------------------

Add this file to your link only when your own source, inline assembly, or a JIT explicitly
references:

      __aeabi_idivmod
      __aeabi_uidivmod

The MSVC ARM CRT does not ship those names. SpiderMonkey's A32 soft-divide path and its wasm
support are the known real-world callers; both are in Varan, which is why the shim exists.

The shim defines four symbols and forwards to the CRT's own helpers. Only two of the four
(__aeabi_idivmod, __aeabi_uidivmod) are ever referenced in practice.

  A PREBUILT COPY IS INCLUDED. You do not have to build it:

      aeabi-shim.lib   1,814 bytes   -- pass this to lld-link
      aeabi-shim.obj   1,466 bytes   -- or this, if you prefer the object

  Both were built by THIS package's clang-cl for thumbv7-unknown-windows-msvc at -O1, with
  -mno-incremental-linker-compatible so the COFF timestamp is zero and the files are
  reproducible. The object's COFF machine field is 0x01C4 (ARMNT), not x86-64: these are
  TARGET binaries, the only ones in this package.

  Verify what it gives you and what it still wants:

      llvm-nm aeabi-shim.lib
        T __aeabi_idiv     T __aeabi_idivmod
        T __aeabi_uidiv    T __aeabi_uidivmod     <- the four it DEFINES
        U __rt_sdiv        U __rt_udiv            <- the two it needs from the MSVC ARM CRT

  Only __aeabi_idivmod and __aeabi_uidivmod are referenced by real code we have seen; the other
  two are defined for completeness.

  To rebuild it yourself from the source beside it:

      clang-cl --target=thumbv7-unknown-windows-msvc -O1 -c aeabi-shim.c -Foaeabi-shim.obj
      lld-link /lib /machine:arm /out:aeabi-shim.lib aeabi-shim.obj

  IT IS OPT-IN. Nothing in this package links it for you, and nothing should: adding it changes
  divide-by-zero behaviour (see below). Add it to your link line only when you hit the two
  undefined symbols.


THE ONE BEHAVIOURAL DIFFERENCE, STATED PLAINLY
----------------------------------------------

Divide by zero TRAPS. The shim forwards to __rt_sdiv / __rt_udiv, which call __brkdiv0 on a
zero divisor. That matches MSVC and it is why rt1 declined to ship compiler-rt's builtins
instead: compiler-rt's __udivmodsi4 does NOT trap -- it returns quotient 0 with an
indeterminate remainder, which is a silent wrong answer where the platform's own helpers
raise. The gate scratch/W3/div0_check.py encodes this and fails the compiler-rt prototype by
design.

If your code divides by zero and relies on a sentinel rather than a trap, this shim will
change your behaviour -- correctly, in rt1's judgement, but change it.


PROVENANCE
----------

Copied verbatim (2,858 bytes, sha256 783adf1989ad18c2...) from the Varan tree, which is the
tree that authored it. Not modified here. Its own header comment carries the register-order
derivation (__rt_* take DIVISOR first; __aeabi_*divmod take numerator first), verified there
by disassembly of the CRT's divide.obj.
