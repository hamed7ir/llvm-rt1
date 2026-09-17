rt2 — the __aeabi divmod shim
=============================

WHY THIS EXISTS

rt2 ships no compiler-rt builtins archive. There is no clang_rt.builtins-*.lib for a
32-bit ARM Windows target in this package, deliberately — see THE TRADE below.

Compiler-generated code never needs this shim. Clang lowers integer division on
ARM32 Windows to the MSVC ARM CRT's own helpers (__rt_sdiv / __rt_udiv), which the
CRT you are already linking against provides. You need the shim only if your own
source NAMES __aeabi_idivmod or __aeabi_uidivmod directly, as SpiderMonkey's
soft-divide and wasm paths do.

WHAT IS HERE

  aeabi-shim.c      2,858 bytes   the source
  aeabi-shim.lib    1,978 bytes   pass this to lld-link
  aeabi-shim.obj    1,630 bytes   or this, if you prefer the object

Both were built by THIS package's clang-cl for thumbv7-unknown-windows-msvc at -O1
with -mno-incremental-linker-compatible, so the COFF timestamp is zero and the files
are reproducible. The object's COFF machine field is 0x01C4 (ARMNT): these are the
only ARM32 TARGET binaries in this package; everything in bin/ is the x64 host
toolchain.

⚠ THESE ARE NOT rt1's SHIM BINARIES. rt1.x ships a shim built by its own 18.1.8
compiler. Do not substitute one for the other: they are target code from different
compilers, and mixing them puts 18.1.8-generated code into a 23.1.1 link for no
reason. The .c source is identical in both packages; only the prebuilt output differs.

WHAT IT GIVES YOU AND WHAT IT STILL WANTS

    llvm-nm aeabi-shim.lib
      T __aeabi_idiv     T __aeabi_idivmod
      T __aeabi_uidiv    T __aeabi_uidivmod     <- the four it DEFINES
      U __rt_sdiv        U __rt_udiv            <- the two it needs from the MSVC ARM CRT

Only __aeabi_idivmod and __aeabi_uidivmod are referenced by real code we have seen;
the other two are defined for completeness.

TO REBUILD IT YOURSELF, from the source beside it:

    clang-cl --target=thumbv7-unknown-windows-msvc -O1 ^
             -mno-incremental-linker-compatible -c aeabi-shim.c -Foaeabi-shim.obj
    lld-link /lib /machine:arm /out:aeabi-shim.lib aeabi-shim.obj

⚠ Run that IN this directory, with bare filenames as written. Passing a full path to
the object produces a LARGER .lib that will not match the bytes shipped here —
lld-link embeds the input path as the archive member name. The .obj is identical
either way. (Measured; it is why the recipe is spelled this way.)

IT IS OPT-IN

Nothing in this package links it for you, and nothing should.

THE TRADE, STATED PLAINLY

Adding this shim changes divide-by-zero behaviour. The MSVC __rt_* helpers RAISE on a
zero divisor; compiler-rt's __udivmodsi4 does NOT — it returns quotient 0 with an
undefined remainder and no fault. That is why this project declined to ship
compiler-rt's builtins archive instead: it would trade a platform-matching trap for a
silent wrong answer. Add the shim to your link line only when you hit the two
undefined symbols above, and know that you are opting into the trap.
