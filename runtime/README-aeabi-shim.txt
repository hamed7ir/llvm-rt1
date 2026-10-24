rt2.1: the __aeabi divide shim
==============================

WHY THIS EXISTS

Code the compiler makes never needs this shim. On ARM32 Windows, clang turns integer division
into calls to the MSVC ARM CRT's own helpers (__rt_sdiv and __rt_udiv), and the CRT you already
link has those. You only need the shim if your own source code CALLS __aeabi_idivmod or
__aeabi_uidivmod by name, like SpiderMonkey's soft-divide and wasm code does.

(This package also has a compiler-rt builtins library for ARM32,
lib/clang/23/lib/windows/clang_rt.builtins-arm.lib. It doesn't define any of the four
integer-divide names this shim defines. The __aeabi_* names it does define are compiler-rt's
floating-point ones, like __aeabi_dadd. The shim has nothing to do with it.)

WHAT IS HERE

  aeabi-shim.c      the source (same as in rt2)
  aeabi-shim.lib    give this to lld-link
  aeabi-shim.obj    or this, if you like the object better

Both were built by THIS package's clang-cl for thumbv7-unknown-windows-msvc at -O1 with
-mno-incremental-linker-compatible, so the COFF timestamp is zero and you can rebuild the same
bytes. The object's machine field is 0x01C4 (ARMNT). Because this compiler built them, they are
not rt2's binaries. The source is the same.

WHAT IT GIVES YOU AND WHAT IT NEEDS

    llvm-nm aeabi-shim.lib
      T __aeabi_idiv     T __aeabi_idivmod
      T __aeabi_uidiv    T __aeabi_uidivmod     <- the four it DEFINES
      U __rt_sdiv        U __rt_udiv            <- the two it needs from the MSVC ARM CRT

TO BUILD IT YOURSELF, from the source next to it:

    clang-cl --target=thumbv7-unknown-windows-msvc -O1 ^
             -mno-incremental-linker-compatible -c aeabi-shim.c -Foaeabi-shim.obj
    lld-link /lib /machine:arm /out:aeabi-shim.lib aeabi-shim.obj

Run that IN this folder, with plain file names like above. lld-link puts the input path into the
archive as the member name, so a full path gives you a bigger .lib that won't match these bytes.
The .obj comes out the same either way.

IT IS OPT-IN. Nothing in this package links it for you.

LICENSE: aeabi-shim.c and the .lib and .obj built from it are under the Apache License v2.0 with
LLVM Exceptions, the same as LLVM (LICENSE.TXT). The LLVM exception means you don't have to give
credit when you link it into your program.

DIVIDE BY ZERO

The shim passes each __aeabi_* call on to the MSVC CRT's __rt_* helper (it swaps two registers
and jumps). So dividing by zero TRAPS (__brkdiv0), exactly like division the compiler makes on
this target. That's how the platform behaves, and it's why the shim exists instead of
compiler-rt's portable __udivmodsi4, which quietly returns a result when you divide by zero.
