# Retained macOS GCC runtime provenance

The existing working runtime is retained. No numerical implementation was replaced.

| Artifact | SHA256 |
|---|---|
| SciPy wheel: scipy-1.17.1-cp311-cp311-macosx_14_0_arm64.whl | a3472cfbca0a54177d0faa68f697d8ba4c80bbdc19908c3465556d9f7efce9ee |
| Wheel member scipy/.dylibs/libquadmath.0.dylib, identical to installed input | 676d86e51a3950f75b41945a758bdb02be1c11fef4f4a45b1994d483228e2504 |
| Accepted d528b98 app's libquadmath.0.dylib, after PyInstaller relocation/signing | bee315a3f4adbf53bb8f73e10c233974fabb74e241e05d4ed89e8ac58478f239 |
| Homebrew GCC 13.4.0 ARM64 Sonoma bottle, rebuild 2 | 06a7bdccc074fedca6ebe1cd078fc8081e6df2502baccb8530bc42714e8af702 |
| GCC 13.4.0 upstream source tar.xz | 9c4ce6dbb040568fdc545588ac03c5cbc95a8dbf0c7aa490170843afb59ca8f5 |
| Homebrew gcc-13.4.0.diff source patch | 60b22ae7f5f78b41e12c51d8c6e99ba933a7e124454fe8cdbff7200505167949 |

PyPI's versioned SciPy 1.17.1 JSON records the exact wheel URL/hash. The wheel's
libquadmath equals the installed file byte-for-byte. PyInstaller's Analysis TOC
identifies that installed scipy/.dylibs member as the bundle input. libgfortran
introduces it as a dynamic dependency. It is ARM64 Mach-O, depends only on the
system /usr/lib/libSystem.B.dylib, and has compatibility/current version 1.0.0.
Its wheel install name is /DLC/scipy/.dylibs/libquadmath.0.dylib; the app uses
@rpath/libquadmath.0.dylib and a fresh ad-hoc signature.

The library contains original Homebrew build paths dated 2025-09-20. The exact
historical bottle above was retrieved from ghcr.io/homebrew/core/gcc/13 and
verified against formula revision af36c21c1e30bdae763ec747504dff4ea25540f3.
Bytes [12912, 343024) of its libquadmath and the SciPy wheel are exactly identical,
including all file-backed Mach-O sections and link-edit data. That region's
SHA256 is acce2928f1f0cf5e613f82a972ba8f1bb43f8725fdb01e3f4af098d59b3c5e98.
Load-command inspection differs only in the library ID path/command size; header
padding and the relocation-dependent code signature account for whole-file
differences. Every file-backed section of libgfortran.5.dylib and
libgcc_s.1.1.dylib also matches this historical bottle. A later bottle was used
only during investigation; it is not the claimed exact build artifact.

The matching recipe pins the source archive and the patch from
Homebrew/formula-patches revision 8bbfd6c920e63f6ed1bf143771bfbfed0a3aaa1d.
Both supplied source and patch passed their publisher/recipe SHA256 checks.
The complete recipe is supplied as gcc13-build-recipe.rb. Source/configure/build
scripts and original copyright/license files are preserved in the archive.

The previous compiler discrepancy is resolved by SciPy's versioned Accelerate
workflow: it uses preinstalled gfortran-13, whereas the generic build script
selects a different compiler distribution for a different path. The installed
wheel's GCC 13.4.0 configuration agrees with the exact bottle evidence.

Primary provenance:
- https://pypi.org/pypi/scipy/1.17.1/json
- https://github.com/scipy/scipy/blob/v1.17.1/.github/workflows/wheels.yml
- https://github.com/Homebrew/homebrew-core/blob/af36c21c1e30bdae763ec747504dff4ea25540f3/Formula/g/gcc%4013.rb
- https://raw.githubusercontent.com/Homebrew/formula-patches/8bbfd6c920e63f6ed1bf143771bfbfed0a3aaa1d/gcc/gcc-13.4.0.diff
- https://ftp.gnu.org/gnu/gcc/gcc-13.4.0/gcc-13.4.0.tar.xz
