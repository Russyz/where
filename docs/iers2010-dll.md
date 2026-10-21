# IERS2010 Windows x64 DLL

This project builds a plain Fortran ABI DLL from the IERS 2010 sources listed by
[`kartverket/where`](https://github.com/kartverket/where). It uses the upstream
`HARDISP.patch` and `dehanttideinel.patch` to make the source callable and
linkable. The DLL exports Fortran
symbols such as `apg_`, `dehanttideinel_`, and `hardisp_`.

## Run on GitHub

The `codex/iers2010-dll` branch in `Russyz/where` runs this workflow on push.
Open the branch's run under **Actions → Build IERS2010 Windows DLL** and download
the **iers2010-windows-x64** artifact after it succeeds. If this workflow is
later merged into the default branch, it can also be started with **Run workflow**.

The artifact contains `iers2010.dll`, `libiers2010.dll.a`, `gpt2_5.grd`, and
the MinGW runtime DLLs. Keep the runtime DLLs next to `iers2010.dll` when using
it. `GPT2.F` may require `gpt2_5.grd` in the process's working directory.

This is a plain DLL, not a Python `.pyd`. Existing Fortran routines use the
compiler's Fortran calling convention: arguments are generally passed by
reference, exported names have a trailing underscore, and strings require
special care. For a stable C ABI, add explicit `BIND(C)` wrappers for the
specific routines your application needs.

The workflow checks that the DLL loads on Windows and that `APG` matches the
reference values published in the IERS source. The GitHub run is the required
final build verification.
