@echo off
call "D:\Program Files\vs22buildtools\VC\Auxiliary\Build\vcvars64.bat" >nul
echo === cl version ===
cl 2>&1 | findstr /C:"Version"
echo === cmake configure ===
cmake -S D:/repo/llvm-rt/llvm-project/llvm -B D:/repo/llvm-rt/build -G Ninja ^
  -DCMAKE_MAKE_PROGRAM="D:/repo/llvm-rt/scratch/R5/ninja.exe" ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DLLVM_ENABLE_PROJECTS="clang;lld" ^
  -DLLVM_TARGETS_TO_BUILD="ARM;X86" ^
  -DLLVM_VERSION_SUFFIX="-rt1" ^
  -DCLANG_VENDOR="Varan" ^
  -DLLD_VENDOR="Varan" ^
  -DLLVM_PARALLEL_LINK_JOBS=2 ^
  -DLLVM_ENABLE_ASSERTIONS=OFF ^
  -DLLVM_INSTALL_UTILS=ON ^
  -DLLVM_INCLUDE_BENCHMARKS=OFF ^
  -DLLVM_INCLUDE_EXAMPLES=OFF ^
  -DLLVM_INCLUDE_DOCS=OFF ^
  -DLLVM_ENABLE_ZLIB=OFF ^
  -DLLVM_ENABLE_ZSTD=OFF ^
  -DLLVM_ENABLE_LIBXML2=OFF ^
  -DLLVM_ENABLE_PDB=OFF ^
  -DLLVM_ENABLE_DIA_SDK=OFF ^
  -DCMAKE_INSTALL_PREFIX=D:/repo/llvm-rt/install-rt1
echo === EXIT %ERRORLEVEL% ===
