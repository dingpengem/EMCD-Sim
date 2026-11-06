EMCD-Sim synthetic structure examples (MIT repository license)

Fe_BCC_a2.8665.cif: exact copy of the tracked alpha_Fe_bcc_Im-3m.cif
fixture introduced by commit 5b4c82bc5d8e5dde60ca1ca3e479951413c4e652;
authenticated against accepted main 3609dfc7. Conventional BCC cell,
2 Fe sites, a=2.8665 angstrom, Im-3m (229). Raw SHA256:
e841d08df6ba5a2860385397a85da36856568d19e72250e1bebaa37885f595df.
The original fixture is retained unchanged; this copy preserves its LF bytes.

Ni_FCC_a3.52.cif: exact copy of the previously authenticated native acceptance
input (SHA256 ad8372ef427a95957a6182d5a7b7f5aaea5899e1464eb0afa8e540ff2f47d67d).
Independently reproduced byte-for-byte offline with ASE 3.29.0:
  write(path, bulk('Ni', 'fcc', a=3.52, cubic=True))
Conventional FCC cell, 4 Ni sites. This illustrative cell is NOT the built-in
Ni default a=3.524 angstrom and is NOT a replacement for the registered XMCD.

Both are synthetic illustrative structures, not experimental refinements.
Redistribution of these project examples is permitted under the accompanying
MIT license (LICENSE.txt); retain its copyright and permission notice.
ASE's software license is separate from these generated numerical coordinates.
Both files were read and geometrically checked through Structure.from_cif.
No external crystallographic database or unlicensed CIF was used.
