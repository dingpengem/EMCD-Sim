# Generalized Multislice EMCD ? local main merge acceptance

## Merge identity

- Reviewed feature: `feat/generalized-multislice`, commit
  `1604bb958a09f8260c0e8cc7ab1a8e966238ae7e` (preserved).
- Reviewed main base: `236893392838ab5bc17dcf1848fd127009f2f048`.
- Main merge commit: `2fadce1e9cf6c1870604f7eafa2fc44bbded4f74`.
- Method: normal `git merge --no-ff`, Git ort strategy; no conflict, squash,
  reset, rebase, force update or history rewrite. Both parents are recorded.
- Merge result's file tree exactly equals the reviewed feature tree.

Main was already checked out in the clean worktree
`C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration`; the merge was
performed there. The original checkout remains on the preserved feature branch
with its 19 pre-existing scientific/source files untouched. Those paths do not
intersect the merge changes. Its existing XMCD formatting difference was checked
numerically against tracked data before merge, without modifying either copy.

## Post-merge validation

**538 tests passed in 525.65 s, with no failures or skips.** JUnit confirms
zero errors. The 1033 warnings are Qt/Matplotlib deprecation/headless-layout
warnings. All ten normal GUI orientation/channeling combinations passed;
solver-only and comparison modes, exports and project roundtrips are included.

A post-suite blanket import check initially also counted the two intentionally
frozen `_baseline_stage_b`/`_baseline_app` test controls. The recorded imports
were audited separately: all **47 production modules** resolve to merged main;
those two controls are exact historical test references, not runtime fallbacks.
Both the raw log and classified import provenance are retained. No source/test
change or numerical rerun was needed for that audit classification.

Source import assertions confirm that actual `emcd_sim` modules load from the
merged main worktree, not the environment's editable feature checkout. Test and
source Git trees are identical between the reviewed feature and merged source;
working-copy text differs only by normal checkout newline handling.

The first complete run in the clean worktree produced 535 passes, two optional
private-WIEN2k-audit skips and one archived-fixture failure. The archive requires
its original exact source-file SHA256; the clean tracked source and that original
source have different formatting but bitwise-identical loaded numeric tables.
No test, reference, source data or threshold was changed to resolve this.
The unchanged archived checks passed at their original paths (3 passed in
11.64 s). The final complete run retained those original fixture paths while
forcing and auditing imports from merged main. Both full logs remain available.

Coverage includes normal GUI [001]/(200), [017]/(200), [117]/(2,-2,0),
[111]/(2,-2,0) and [710]/(002), Single/Double BW/MS/Both, indexed diffraction,
Bragg alignment, Thales detectors, EELS/maps, raw/relative display, project
save/reopen, legacy-frame guards, cancellation and resource admission.
No large scientific convergence study or production scan was repeated.

Independent post-merge checks confirm:

- Zero production imports of `ni_017_geometry` or `ni_117_geometry`.
- The [111] 0.1094% limitation warning is present for BW, MS and Both.
- Saved raw [117] L3 magnetic mirror-even fractions remain 0.1745790961 BW and
  0.1745768584 MS for the matched historical coarse-grid control. Maximum legacy
  raw-map changes remain 0 BW and 2.4869e-14 MS, without recalculation.
- Packaging spec syntax passes. No executable or ZIP was built.
- Public package version remains `0.6.1b3`; no version tag or release was created.

## Integrity and working trees

**323 protected files and all 204 production checkpoints are unchanged.**
All 19 pre-existing user files retain their exact pre-merge byte hashes.
Before adding this acceptance record, main's working tree was Git-clean; after
its documentation-only commit it must be clean again. The original feature
checkout intentionally retains its pre-existing modified XMCD formatting and
untracked scientific files; none is included in main's commits.

The original workspace's protected-file manifest was checked before and after
validation: all 323 entries, including 204 production checkpoints, must retain
exact SHA256 hashes. The 19 pre-existing user files are separately checked against
the pre-merge snapshot. Historical arrays/reports and licensed companions are
not regenerated, normalized, moved or added to Git.

The main worktree has an ignored local outputs junction to the existing results
workspace for read-only references and new disposable test artifacts. It does
not add scientific data to the source tree. The acceptance documentation is a
separate documentation-only commit after the tested merge; solver/test/package
content remains identical to the tested merge commit.

## Readiness and remaining limits

**GO: local main is ready for an ordinary GitHub push and a Windows EXE candidate
build, when separately authorized.** Neither action was performed. A read-only
`git ls-remote` check observed GitHub main still at the reviewed base, so the
validated local history is a normal fast-forward push candidate at that check.
Remote state can change before a later push; no force operation is authorized.

This is the bounded research implementation described in
[scientific merge readiness](GENERALIZED_MULTISLICE_MERGE_READINESS.md).
The lower-support [111] raw change of 0.1094% still exceeds the unchanged 0.1%
gate and is not quantitatively certified. Passing enlarged-MS increments do
not certify independently enlarged BW, all thicknesses, arbitrary mistilts or
full-spectrum convergence. Its warning and configuration scope remain intact.

The projected IAM/XMCD-effective MDFF, finite reciprocal support, approximate
longitudinal treatment and arbitrary intensity scale retain their documented
physical limitations. No complete DFT MDFF, Atomic 3D/HOLZ implementation,
experimental energy/count calibration or standalone clean-machine acceptance
is claimed. No simulation physics or numerical threshold changed in this merge.

Detailed evidence: `outputs/generalized_multislice_local_merge/`, including
premerge snapshots, both full test runs, JUnit XML, import provenance, archived
fixture audit, asymmetry/warning checks and final protected-file verification.
