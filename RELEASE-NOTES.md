# rt2.3 release notes

**Build:** 2026-11-08, clang `ecc7a88742db83ce2316082eb80d23183a8d1e5e`.
`clang-cl --version` prints `Varan clang version 23.1.1-rt2.3 (ecc7a88742db83ce2316082eb80d23183a8d1e5e)`.

rt2.3 is rt2.2 with 2 more patches, so 32 in all, and its LLVM is built with zlib 1.4 now. The base is still LLVM
23.1.1. It's a full toolchain for C and C++ on ARM32 Windows (`thumbv7`) with `clang-cl` and `lld-link`. It doesn't
overlay anything: unpack it and use it. clang's own headers are in `lib/clang/23/include`.

It does **not** include Microsoft's C and C++ headers and libraries or the Windows SDK. For ARM32 you need Visual
Studio 2022 Build Tools with the ARM build tools, and a Windows SDK that still has ARM32 libraries (10.0.19041 has
them, 10.0.26100 doesn't).

The revision in the version string is the first 40 hex digits of the sha256 of `patches/rt23-vs-23.1.1.patch`,
the full diff from clean `llvmorg-23.1.1`. So you can check which source a binary came from.

## What's new since rt2.2

Both new patches are mine. The bugs were found by the work porting Kodi to Windows RT 8.1 ARM32, which builds with
rt2.2:

| patch | what was wrong | what you saw without it | tests |
|---|---|---|---|
| 0027 | on ARM32 clang wrote the C++ throw information (ThrowInfo, CatchableTypeArray, CatchableType) with absolute addresses. MSVC's runtime reads them there as offsets from the image base, like on x64 | every C++ `throw` crashed on ARM32 Windows | 1 new |
| 0028 | `__ARM_SIZEOF_WCHAR_T` was always 4 | on Windows ARM32 and ARM64, where `wchar_t` is 2 bytes, the macro said 4 | 1 new, 1 changed |

0027 keeps the RTTI absolute, because MSVC's runtime reads that as absolute on ARM32. Only the throw tables changed.

**zlib.** LLVM is built with zlib 1.4 now, as a static library, so it's inside the tools. I added it for Venetium's
PGO build. What it changes:

- The names in a PGO profile are compressed. `-fprofile-generate` objects get smaller: in my test, the names of 400
  functions went from 22,803 bytes to 1,054 in an ARM32 object.
- `llvm-profdata` reads profiles with compressed names. rt2.2's couldn't.
- `llvm-objcopy` can compress and decompress ELF debug sections. COFF has no compressed sections, so
  `llvm-objcopy --compress-sections` on a `.obj` still says "option is not supported for COFF", as in stock LLVM.

zlib is the released `zlib-1.4.tar.gz`, not changed, built with `/MD` like LLVM. Its license is
`licenses/zlib-LICENSE.txt`.

0027 and 0028 were each reviewed by a separate AI session that didn't write it and was told to break it. 0028's
review found a case the first version got wrong (the host target of an offloading compile), and the fixed version
was reviewed again.

## Things that work differently now

- **Rebuild every ARM32 object that throws a C++ exception, with rt2.3.** Objects from rt2.2 or older keep the old
  tables, and they crash when they throw. 0027 only changes the tables clang writes for a `throw`.
- **`__ARM_SIZEOF_WCHAR_T` is 2 on Windows ARM32 and ARM64** now, the size of `wchar_t` there. With `-fshort-wchar`
  or `-fwchar-type` it follows the option, as before.
- **Merge PGO profiles from rt2.3's builds with rt2.3's `llvm-profdata`.** The names in them are zlib-compressed,
  and rt2.2's says "profile uses zlib compression but the profile reader was built without zlib support".
- `lld-link --version` still prints `Varan LLD 23.1.1`, with no rt2.3 in it. Check lld by its sha256.

## How it was tested

Everything here ran on my build server, not on an ARM32 device.

- **lit:** the 3 new or changed tests ran on the published rt2.2 binaries, on an rt2.3 test build and on the rt2.3
  binaries in this archive. All 3 fail on rt2.2 because of their bug and pass on rt2.3. rt2.2's 20 tests ran in the
  same three places and give the same results as on rt2.2: 18 pass, and the 2 that need back ends I didn't build
  (AArch64 and PowerPC) are unsupported in all of them.
- **Suites:** 19,256 tests in 14 suites: rt2.2's 10 (ARM and X86 CodeGen, ARM MC and its disassembler, lld COFF,
  clang CodeGen, InstCombine, Instrumentation, GlobalsModRef and llvm-lib), clang's Preprocessor and CodeGenCXX for
  0027 and 0028, and llvm-profdata's and llvm-objcopy's for zlib. No test fails on rt2.3 that passes on rt2.2. The
  only failure is the same one as in rt2.2: rt2.1's own `arm-thumb-thunks-no-converge.s`, which loses lld's message
  inside the real llvm-lit. With zlib, 15 tests that rt2.2 skipped run now, and all of them pass. The 3 tests that
  check a build without zlib are skipped now.
- **0027 against MSVC:** I compiled the same C++ with MSVC's ARM32 `cl` and with clang, and compared the
  relocations of every throw-table field. rt2.3's are image-relative (`ADDR32NB`) where MSVC's are, to the same
  symbols, and the RTTI stays absolute (`ADDR32`) like MSVC's. rt2.2's throw tables were all absolute. Venetium's two
  probes give the same: a type with a destructor and a copy constructor (all five fields image-relative, like MSVC)
  and an RTTI one (all absolute, like MSVC).
- **0028:** `static_assert(__ARM_SIZEOF_WCHAR_T == sizeof(wchar_t))` compiles for ARM32 and ARM64 Windows with rt2.3,
  and fails with rt2.2.
- **zlib:** with the rt2.3 tools, an i686 program built with `-fprofile-generate` ran, `llvm-profdata` merged its
  profile, and the `-fprofile-use` build gave no warning about a missing or mismatched profile. A source with one more
  function did warn about it, so the check works. rt2.2's `llvm-profdata` refuses that profile. `llvm-objcopy`
  compressed an ELF object's debug sections and decompressed them back to the same bytes.
- **0026's instruction list:** rt2.3's `llvm-mc` gives exactly rt2.2's output for every line of my bug report's
  list, byte for byte.
- **compiler-rt:** all six libraries, the staged `rtdiv` one and the `__aeabi` shim are built by rt2.3. They have the
  same code and data as rt2.2's, member for member.
- **Headers:** all 303 files in `lib/clang/23/include` are rt2.2's, byte for byte.
- **rustc:** rebuilt on rt2.3 in one bootstrap run. Against rt2.2's rustc, a hello program and a division test give
  the same objects on all three targets, and both rustcs' builds for i686 and x86_64 **ran** with the same output. In
  the standard library no function changed, in LLVM IR or in machine code. 22 of the 45 files per target are byte for
  byte the same, and the others differ only in build stamps: the LLVM version and revision inside them, and the DLL's
  link time and debug ID.

## What was not tested

- Nothing ran on an ARM32 device. I checked 0027 against MSVC's objects, not by throwing an exception on a device.
  The Kodi port's exception test on the device comes next.
- Venetium isn't rebuilt with rt2.3 yet.
- The Rust standard library for `thumbv7a` only runs on an ARM32 device, so it isn't run either.

## Where it came from

The toolchain was built from `patches/rt23-vs-23.1.1.patch`: rt2.2's tree plus 0027 and 0028, as one
`git diff --binary` from clean `llvmorg-23.1.1`. I checked it by applying it to a clean tree: it gives the same tree
as the commits it was made from. `patches/origin/` has every patch on its own. See its `README.txt`.

I'll send 0027 and 0028 upstream. That's separate work.

**AI assistance:** I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the
work. Every test result here was really run. What was not tested is listed above.

**License:** Apache License v2.0 with LLVM Exceptions, same as LLVM. See `LICENSE.TXT`. lld-link and llvm-mt include
libxml2, which is MIT, and the tools include zlib, under the zlib license (both notices are in `licenses/`). The
Microsoft VC runtime DLLs in `bin/` are Microsoft's redistributable files and are not under either license. See
`MODIFICATIONS.txt`.
