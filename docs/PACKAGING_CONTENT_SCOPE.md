# Proposed additive packaging content scope v1

This proposal starts from accepted main `3609dfc762749024a3c6726c3763ef33f3e46482`.
It changes only four packaging files, adds pinned package assets/content checks,
and adds source-guard infrastructure. Production and numerical code is unchanged.

The original editor manifest, its parent archive, historical manifests, scientific
pins and skip record remain immutable. The new six-file parent archive contains
Git blob bytes from accepted main. Its inventory records Git blob IDs and raw
and canonical SHA256. The additive manifest records a closed modified set and
explicit asset additions. The new loader independently pins manifest canonical
SHA256 and parent archive raw SHA256. Its own review bootstrap identity belongs
to the complete independently reviewed patch; the manifest is not its own trust
anchor. Builders never generate or adopt pins.

The editor guard first authenticates its original evidence, then authenticates
this separate layer. Only the four specified packaging current identities are
superseded. Original expected parent comparisons remain in place; every other
editor/protected path retains its original identity. Binary/license/CIF assets
are checked raw in the additive layer; canonical text uses UTF-8-sig decode,
CRLF-to-LF only, UTF-8 encode. No checkout bytes are rewritten. The isolated
mutation fixture copies the new layer too and retains every original assertion.

Independent review must approve the complete patch, new bootstrap pins and both
manifests before commit/merge. This is a required scope amendment, not an automatic
refresh of the historical source guards. Targeted mutation tests must prove
rejection of changed packaging, CIF/license bytes, evidence and physics sources.

After review/commit/controlled merge, use the recorded dependency environment and
a fresh internal build root and label tied to the new accepted commit. Run the
documented build script, inspect the required-content post-collection result,
new ZIP/executable/distribution hashes, and unchanged source inventories. Extract
outside the repository; verify both CIFs can be selected and read and license
collections can be opened offline. Run native launch/editor/project save-open
smokes and affected packaged workflows. Do not reuse the prior ZIP identity for
the new artifact. Full numerical regression need not be repeated for this asset
change absent a concrete failure or review requirement. Offline isolation and
upstream HDF5 comparison remain UNVERIFIED. GPL/LGPL redistribution obligations,
including corresponding source, remain a separate release review requirement.
