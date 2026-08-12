@echo off
call "D:\Program Files\vs22buildtools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (echo VCVARS FAILED & exit /b 1)
"D:\repo\llvm-rt\scratch\R5\ninja.exe" -C "D:\repo\llvm-rt\build" %*
exit /b %errorlevel%
