# Provider licensing and provenance

PASS for public redistribution of the pinned Adaptive coefficient subset with Apache-2.0 conditions. The original legacy table remains unlicensed external data and is NOT bundled. Scientific publication or a Python translation was not treated as permission.

Author repository: https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/tree/1667babb2c5bdb44a0535438b846eb1bbfbc03ac

The pinned repository LICENSE and author README explicitly declare Apache-2.0 for the project and deposited data. Full LICENSE, NOTICE, attribution, pin and transformation are included beside coefficients; EMCD-Sim MIT does not relicense those data. No upstream NOTICE was present in the pinned tree. Only the adaptive_dirac_pade coefficient subset is redistributed. Exact float32 values are serialized as exact binary64 JSON values; no refitting, new interpolation or digit truncation. Offline extraction requires h5py; production uses only existing NumPy and ASE dependencies. Upstream Python evaluator, atomx, HDF5 reference, SciPy, SymPy and plotting package are not redistributed by this feature. Their upstream dependency declarations do not automatically become EMCD runtime dependencies. The source repository/preprint describes authorship and atomic generation; this audit cannot independently recreate Dirac–Fock orbitals or establish journal acceptance.

| artifact | SHA256 |
|---|---|
| upstream_hdf5_sha256 | 4d623613d3fe475211d1b78b7965d9604bb8748f9fcfe74700d0ffe3b345cc78 |
| coefficient_data_sha256 | a67788f59b426c07cf27913e023ed08e3a748fdb6b634d0bb5eed6b4ecf77b5c |
| reference_data_sha256 | 2703206ccb8c3c26fe3a330856c4846fa365e6e7e130c076ccce20847daf8366 |

Physical convention is independently established by [the manuscript Fourier equations](https://arxiv.org/html/2608.14934v1): exp(-2*pi*i*g.r), density sinc(2*pi*g*r), and fe=(Z-fx)/(2*pi²*a0*g²). Thus g is crystallographic 1/d, not STL or angular Q. Local radial quadrature of fitted densities verifies this convention without an extra potential factor. fe is in angstrom; IAM subsequently applies its original potential conversion and propagation gamma.

| check | result |
|---|---|
| all118 reference-grid worst relative discrepancy | 0.000112288683 |
| original formula max relative arithmetic discrepancy | 1.30065954e-14 |
| 65-digit formula max relative discrepancy | 1.12242853e-14 |
| radial Fourier identity max relative discrepancy | 1.4297928e-08 |
| 10000 Ni factors average seconds (local machine only) | 0.00596346333 |

Source-compatible algebra, numerical stability and scientific accuracy are separate claims. Values are finite/positive at origin, subnormal inputs and selected points through36 for all118. The accepted adapter range is 0<=g<=36 inverse angstrom, inclusive; all other inputs fail rather than extrapolate. Reference discrepancies measure the fit against the author-deposited reference, not an independent experiment or universal absolute accuracy. This is a 2026 submitted manuscript/preprint parameterization. Neutral atoms omit bonding, ions, absorption and TDS.

The external legacy guard remains STL=0 or .04<=STL<=6 for all44 XF/Mott elements; EF retains source-specific limits. Small nonzero supercell vectors below .08 inverse angstrom fail explicitly under XF/Mott. The unified provider evaluates such vectors analytically and continuously without dividing by g² or changing the legacy source.
