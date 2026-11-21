# Automatic crystallographic site grouping — Phase 1

Baseline: accepted candidate source `6b917eda7119982ac5c9d68f8b9a79aeb8299dca`.
This source-only feature is developed separately on `feat/v0.9.0-crystal-grouping`;
the accepted release EXE and its source kit are unchanged.

## Minimal implementation

On CIF import, ASE retains the CIF tags and original atom ordering. spglib 2.7
identifies the space group, input-cell `equivalent_atoms` orbits and Wyckoff
letters at a fixed **1e-5 Angstrom** distance tolerance (automatic angle tolerance).
No standardization, atom sorting, position idealization or progressively relaxed
tolerance is applied. Orbit membership, not element or Wyckoff letter alone,
defines each suggestion. Distinct orbits of the same element remain distinct.

CIF origin choices are honored when compatible with the inferred space group.
In particular, origin choice 2 of Fd-3m yields spinel 8a/16d/32e rather than the
equivalent origin-choice-1 labels 8b/16c/32e. Wyckoff multiplicity refers to the
standard conventional cell; the displayed atom count refers to the actual input
cell, including a supercell. Original ASE indices always refer to the imported
structure, never standardized or displayed-replica indices.

CIF labels are associated through ASE's `spacegroup_kinds` and checked against
the species and orbit. Validated labels are retained in provenance/tooltips;
they cannot merge or split a symmetry orbit. Stable initial names use the
element and, for multiple orbits, A/B/etc. in Wyckoff-letter order. These letters
are structural names, not inferred valences, magnetic directions or MDFF models.

The existing editor initializes **structural drafts**, including nonmagnetic
elements such as oxygen. Their magnetization and provider are explicitly unset.
Global M mode remains active and legacy calculations keep their interpretation.
Select a group once, enable Local mode and enter a direction explicitly to edit
all its atoms. No arrows appear for undeclared directions. MDFF binding and
executable `MultiSiteIonization` still require all relevant declarations.
Structural oxygen contributes to the elastic crystal, not automatically to an
Fe-only ionizing-atom denominator. Unneeded draft ionizing rows can be deleted
using the existing editor; the original crystal is unchanged.

Existing user rows are never overwritten by suggestions. Group count, Wyckoff
position, original indices and selected-group information are shown in the
existing viewer. Membership/provenance use the existing project configuration
metadata and structure snapshot; no new project framework or scientific model
is introduced. The CIF occupancy-to-atom mapping is also preserved through the
legacy Global-mode restoration bridge.

## Limits and manual fallback

Partial/disordered occupancy, invalid geometry or unavailable symmetry support
produces an explanatory manual-grouping status, not a chemical-element merge.
Ordinary structural viewing remains available; existing ordered-site calculation
validation remains in force. Low-symmetry structures can legitimately yield one
orbit per atom. A distortion below the stated tolerance is indistinguishable
from symmetry within that tolerance; these are suggestions, not magnetic or
spectroscopic equivalence claims. CIF group disagreements are recorded. Labels
that cannot be validated are ignored with a warning. Magnetic space groups,
magCIF and quantitative moment inference are outside Phase 1.

The new GUI dependency is spglib >=2.7,<3 (Windows development pin 2.7.0). A future
separately authorized candidate build must bundle it and its applicable license;
this phase does not rebuild or alter accepted artifacts.

## Verification scope

`tests/test_crystallographic_sites.py` covers the 56-atom inverse-spinel CIF,
independent four-/six-oxygen coordination checks, shuffled original indices,
supercells, one-site Ni/Fe, inequivalent same-element sites, distortion/vacancy,
partial occupancy, invalid CIF labels, import/editor/Save/Open integration,
direction drafts and unchanged MDFF source/frame rejection.

The existing Apply restriction is retained. See the separate
[Phase 2 proposal](PHASE2_GROUP_MAGNETIZATION_MDFF.md). Final execution results and
source identity are supplied at the independent acceptance review gate.

Minimal closure verification: three focused cases passed (accepted deletion
through Save/Open, and Ni/Fe CIFs without a numbered origin choice). The native
Windows source-GUI workflow passed import, 8a/16d/32e counts 8/16/32, explicitly
entered direction drafts, undeclared oxygen without arrows, Cancel/reopen, and
structural project Save/Open with provenance. The compact group table requires
scrolling or keyboard navigation. The prior source-guard rerun was interrupted
and remains **incomplete**; its pending current-source pin edits were reviewed,
not reverified by a broad suite. No full application regression, scientific
benchmark rerun, candidate rebuild or release acceptance is claimed.

Primary interface references: [spglib dataset](https://spglib.readthedocs.io/en/v2.7.0/dataset.html)
and [ASE CIF importer](https://docs.ase-lib.org/_modules/ase/io/cif.html).
