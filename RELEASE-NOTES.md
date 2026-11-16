# rt2.4 release notes

**Build:** 2026-11-13, clang `f6e5f8e02a8c69d0479b5623215b8a8b8fcd2e01`.
`clang-cl --version` prints `Varan clang version 23.1.1-rt2.4 (f6e5f8e02a8c69d0479b5623215b8a8b8fcd2e01)`.

rt2.4 is rt2.3 with 6 more patches, so 38 in all. The base is still LLVM 23.1.1, built with zlib 1.4 like rt2.3.
It's a full toolchain for C and C++ on ARM32 Windows (`thumbv7`) with `clang-cl` and `lld-link`. It doesn't overlay
anything: unpack it and use it. clang's own headers are in `lib/clang/23/include`.

It does **not** include Microsoft's C and C++ headers and libraries or the Windows SDK. For ARM32 you need Visual
Studio 2022 Build Tools with the ARM build tools, and a Windows SDK that still has ARM32 libraries (10.0.19041 has
them, 10.0.26100 doesn't).

The revision in the version string is the first 40 hex digits of the sha256 of `patches/rt24-vs-23.1.1.patch`,
the full diff from clean `llvmorg-23.1.1`. So you can check which source a binary came from.

## What's new since rt2.3

All 6 new patches are mine, and five of them are in C++ exception handling. The work porting Kodi to Windows RT 8.1
ARM32 found five of the bugs: it builds Kodi and its libraries with this toolchain and runs their tests on my Surface
RT. It hit 0029 and 0031 on the device, and 0032 to 0034 while building Kodi. I found 0030 myself while sending the
C++ exception work upstream (it's llvm/llvm-project#239929), and the port's exception test checked it on the device.

| patch | what was wrong | what you saw without it | tests |
|---|---|---|---|
| 0029 | on ARM32 clang wrote each catch handler entry with a field only 64-bit Windows has, so 20 bytes. MSVC's runtime reads 16 there | when a `try` had more than one `catch`, taking the second or a later one jumped to garbage | 1 changed |
| 0030 | the code after a `catch` was placed inside the catch funclet | MSVC's runtime took that code as part of the catch, so an exception thrown there was handled as if it came from inside the catch | 1 new |
| 0031 | a call that doesn't return (a `throw`, a rethrow, `abort()`) could be the last instruction of a function or funclet. Then its return address is the start of the next one, and MSVC's runtime unwinds through the wrong one | in the Kodi port's test, a rethrow in a `catch` was caught again and again until the stack overflowed | 1 new |
| 0032 | clang didn't count the few bytes of padding before each funclet when it placed a function's constants | some functions with `try`/`catch` didn't compile: "out of range pc-relative fixup value" (Kodi's InputManager.cpp) | 1 new |
| 0033 | `llvm-objdump` took an ARM32 DLL's export addresses with the Thumb bit still set | `llvm-objdump -d` started every export one byte too late, so its code came out as garbage | 1 new |
| 0034 | with debug info, 0030 could load a catch's continuation address inside the epilogue | some catch blocks didn't compile with `/Zi` or `/Z7`: "Incorrect size for ... epilogue" (Kodi's FFmpeg.cpp with `-fprofile-generate`) | 1 new |

0034 fixes my own 0030, so rt2.3 never had that bug. 0033 is only in `llvm-objdump` and changes nothing that's
built. 0031 is what MSVC does too: its ARM32 `cl` puts a `udf #254` trap after such a call, and so does rustc on
Windows.

## Things that work differently now

- **Rebuild every ARM32 object that throws or catches a C++ exception, with rt2.4.** Objects from rt2.3 or older
  keep the old catch tables and the old code layout. Libraries you link count too.
- **A trap follows every call that doesn't return**, on Windows ARM32 (0031). It's 2 bytes each, so ARM32 code gets
  a little bigger. The Kodi port's exception test program got 191 of them in its Release build.
- `lld-link --version` still prints `Varan LLD 23.1.1`, with no rt2.4 in it. Check lld by its sha256.

## How it was tested

**On a device.** The Kodi port ran its tests with rt2.4's builds on my Surface RT (Windows RT 8.1, Tegra 3):

- Its C++ exception test, 56 cases, passes in a Release and a debug build, and its output is the x86 build's, byte
  for byte. That was with the rt2.4 builds that had 0031 and 0032. 0033 and 0034 don't change that program: this
  final build gives the same code, except the version string inside.
- Kodi built with rt2.4 runs: its UI, touch, add-on installs over HTTPS, a 1080p H.264 video with hardware decoding,
  and a trailer with sound. Kodi RT 1.1's kodi.exe and its FFmpeg are built with this final build, with PGO and
  ThinLTO (the other libraries in it are from rt2.4's earlier builds). It plays 720p 10-bit HEVC and H.264 at 24 fps
  on the Surface RT, and it runs on a Surface 2 too.
- FFmpeg's and dav1d's own assembly tests pass (checkasm: 1,140, then 1,300 with the port's NEON patch, and 2,039),
  and H.264 decodes match an x64 build. FFmpeg built with this final build ran 126 decodes with no errors.
- Kodi's libraries pass their tests: OpenSSL with a TLS 1.3 handshake, curl, FreeType and HarfBuzz, SQLite, PCRE2's
  JIT, libass, iconv, and C++ exceptions thrown inside fmt, nlohmann json and Exiv2. So do Python 3.14 for ARM32,
  ctypes, pycryptodome and Pillow.
- The other bugs the port hit on the device were Kodi's own, and they're fixed in Kodi. One crash ended with exit
  code 0xC00000FF (a bad function table during unwinding) instead of an access violation. I traced it to Kodi's crash
  handler: it lets StackWalk64 change the crash's own context, and Windows then unwinds that thread from a wrong
  place. The unwind tables of both kodi.exe builds check out entry by entry, and the crashed thread whose context
  wasn't changed unwinds cleanly from the crash all the way out of kodi.exe.

The rest ran on my build server:

- **Against MSVC:** I compiled the same C++ with MSVC's ARM32 `cl` and with clang. rt2.4's catch handler entries are
  16 bytes apart like MSVC's, and the code after a catch is in the parent function like MSVC's. rt2.3's entries were
  20 bytes apart, and it put that code in the catch funclet. In the Kodi port's exception test program, no call has
  its return address in the next function, like MSVC's build of it. rt2.3's Release build has 154 such calls.
- **The Kodi port's own repros:** its file for 0032 compiles with rt2.4 and fails with rt2.3. Its file for 0034
  compiles with rt2.4, fails with the rt2.4 build before 0034, and compiles with rt2.3. `llvm-objdump` shows its
  DLL's two exports at their real addresses, and rt2.3's doesn't.
- **lit:** the 6 new or changed tests ran on the published rt2.3 binaries, on an rt2.4 test build and on the rt2.4
  binaries in this archive. All 6 fail on rt2.3 because of their bug and pass on rt2.4. The 23 tests from rt2.2 and
  rt2.3 give the same results in all three: 21 pass, and the 2 that need back ends I didn't build (AArch64 and
  PowerPC) are unsupported.
- **Suites:** 19,260 tests in the same 14 suites as rt2.3. No test fails on rt2.4 that passes on rt2.3, and the 4
  new tests pass. The only failure is the same one as in rt2.2 and rt2.3: rt2.1's own
  `arm-thumb-thunks-no-converge.s`, which loses lld's message inside the real llvm-lit. After 0031, 0032 and 0034 I
  also ran the ARM, Thumb, WinEH and COFF tests (2,705, and 3,137 with all of `llvm-objdump`'s at the end): none
  failed.
- **rt2.3's checks:** 0027 against MSVC's objects, Venetium's probes, 0028, zlib's PGO round trip and the 0026
  instruction list still give rt2.3's results.
- **compiler-rt:** all six libraries, the staged `rtdiv` one and the `__aeabi` shim are built by rt2.4. The x86 and
  x64 ones have the same code and data as rt2.3's, member for member. In the ARM ones, the only change is 0031's
  traps after calls that don't return, and what they move (one jump table's offsets, and one `bl abort` tail that
  now comes twice). The shim has the same code.
- **Headers:** all 303 files in `lib/clang/23/include` are rt2.3's, byte for byte.
- **rustc:** rebuilt on rt2.4 in one bootstrap run. Against rt2.3's rustc, a hello program and a division test give
  the same objects on all three targets, and both rustcs' builds for i686 and x86_64 **ran** with the same output. In
  the standard library no Rust function changed, in LLVM IR or in machine code. rustc already puts 0031's traps into
  Rust code on Windows, and its `thumbv7a` target aborts on panic, so it has no catch blocks. The only change is the
  C profiler runtime it bundles for `thumbv7a`: 0031's 29 traps, as in compiler-rt's own copy. 22 of the 45 files per
  target are byte for byte the same, and the others differ only in build stamps.

## What was not tested

- The exception test didn't run on the device with this exact build. It gives the same code as the build that ran,
  except the version string.
- In my replay of the 0xC00000FF crash, the destructors that Windows runs on the way out weren't run. I replayed only
  the unwinding itself.
- Venetium isn't rebuilt with rt2.4 yet. Chromium builds without C++ exceptions, so of the new patches only 0031's
  traps change its code.
- The Rust standard library for `thumbv7a` still runs on no device here.

## Where it came from

The toolchain was built from `patches/rt24-vs-23.1.1.patch`: rt2.3's tree plus 0029 to 0034, as one
`git diff --binary` from clean `llvmorg-23.1.1`. I checked it by applying it to a clean tree: it gives the same tree
as the commits it was made from. `patches/origin/` has every patch on its own. See its `README.txt`.

I sent all six upstream too: 0029, 0030 and 0034 are part of llvm/llvm-project#240693, 0031 is #242026 (written
there as its own pass, which a reviewer approved), 0032 is #242153 and 0033 is #242496.

**AI assistance:** I made the patches, tests and documents with a lot of help from AI. I directed and reviewed the
work. Every test result here was really run. What was not tested is listed above.

**License:** Apache License v2.0 with LLVM Exceptions, same as LLVM. See `LICENSE.TXT`. lld-link and llvm-mt include
libxml2, which is MIT, and the tools include zlib, under the zlib license (both notices are in `licenses/`). The
Microsoft VC runtime DLLs in `bin/` are Microsoft's redistributable files and are not under either license. See
`MODIFICATIONS.txt`.
