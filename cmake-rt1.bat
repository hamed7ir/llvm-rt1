@echo off
call "D:\Program Files\vs22buildtools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (echo VCVARS FAILED & exit /b 1)
"C:\Program Files\CMake\bin\cmake.exe" %*
exit /b %errorlevel%
