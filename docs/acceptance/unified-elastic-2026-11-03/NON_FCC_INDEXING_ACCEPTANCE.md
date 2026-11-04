# Non-FCC indexing acceptance

PASS for the specified cells and settings. CIF fixtures in this directory preserve the supplied metric and atomic basis through ASE. Cross-product reciprocal bases and Cartesian zone/target frames provide independent references, rather than calling production reciprocal routines twice.

| case | zone | target | beams | coordinate max error (1/angstrom) | structure-factor error (angstrom) | Hermitian error |
|---|---|---|---|---|---|---|
| bcc_fe | (0, 0, 1) | (1, 1, 0) | 13 | 1.11022302e-16 | 0 | 0 |
| bcc_fe_110_zone | (1, -1, 0) | (1, 1, 0) | 11 | 1.11022302e-16 | 0 | 0 |
| cscl | (0, 0, 1) | (1, 0, 0) | 25 | 0 | 0 | 0 |
| hex_zno | (0, 0, 1) | (1, 0, 0) | 19 | 1.11022302e-16 | 3.55271368e-15 | 0 |
| monoclinic | (0, 1, 0) | (1, 0, 1) | 31 | 1.2490009e-16 | 4.04127281e-15 | 0 |

BCC Fe (100) is absent and (110) is retained in BOTH [001] and [1,-1,0]: h*u+k*v+l*w=0. The requested text excluding (110) from [001] contradicted this zone law; no artificial exclusion was introduced. CsCl is primitive cubic: (100)=fCs-fCl survives; (200)=fCs+fCl. ZnO basal reciprocal axes meet at 60 degrees with |a*|=2/(sqrt(3)*a). Monoclinic beta=107 degrees exercises a nonorthogonal reciprocal metric.

Offscreen Qt tests compare actual rendered offsets and signed labels against analytical coordinates, click the negative target, independently check Bragg alignment, and change zone/target/CIF context, full/two-beam bases and provider. Invalid zero/out-of-zone targets and oversized searches fail explicitly. Four-index Miller–Bravais input is unsupported. Labels refer to the ASE-imported cell; no automatic primitive reduction is performed. An externally transformed cell requires an explicit hkl basis transformation.

Actual GUI diffraction exports: [Fe001](gui_bcc_fe.png), [Fe110](gui_bcc_fe_110_zone.png), [CsCl](gui_cscl.png), [ZnO](gui_hex_zno.png), [monoclinic](gui_monoclinic.png). These display computed elastic preview intensities on the indexed GUI plot, rather than a separate plotting implementation.
