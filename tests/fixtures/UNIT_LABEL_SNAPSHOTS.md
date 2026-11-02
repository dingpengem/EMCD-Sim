# Immutable unit-label source evidence

`unit_label_sources_v1.zip` is a **source-only test fixture**, not a Windows
application archive or scientific output. No archived Python is executed.

The manifest identifies exact commits, trees, Git blob IDs and SHA256 hashes:

- `pre_unit`: cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5, all nine audited modules
  and historical Windows Beta 3 documentation.
- `unit`: b3edf65e8f539b6f4e37e35b8b35144566b7838a, the same nine modules.
- `zolz`: dfd60115e73cf0fcfc4c7d7c44432c667c771b34, only the separately reviewed
  `gui/app.py` implementation.

Tests verify pinned manifest/archive hashes and every source entry's SHA256 and
Git blob ID, without calling Git or accessing the network. Manifest/current-source
text permits LF/CRLF checkout normalization; archived Git blob bytes are exact.
The historical AST comparison remains pre-unit versus unit, including app.py.
A separate current-source guard accepts only the verified unit sources plus the
reviewed ZOLZ app version. It protects constants, worker-policy strings, reciprocal
conventions, project keys and executable behavior, including changes the historical
string-normalizing comparison alone could not detect. Future intentional source
changes need explicit review and a pinned scope update; the guard never self-updates.

Maintainers with the three Git objects can reproduce the fixture using
`python tests/fixtures/build_unit_label_sources.py`. The builder uses fixed entry
timestamps, stable ordering and Git-verified bytes; compressed ZIP bytes can depend
on the Python/zlib version, so changed archive hashes require review. Ordinary
installed/exported-tree tests use the committed fixture and never run this builder.
