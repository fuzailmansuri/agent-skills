# Manifests and cross-repository changes

The effective `repo` manifest includes the selected manifest revision, includes,
local manifests, project overrides, groups and per-project revisions. Inspect
`.repo/manifest.xml` and local manifests; use `repo manifest -r` when available to
record checked-out revisions. The manifest selects projects, while product/build
configuration determines what is compiled and installed.

Keep each component in its existing repository and branch model. Localize the
projects that differ from upstream; avoid inventing a separate branch across every
repository for a change affecting only one component. Isolate work from a running
build or unrelated local modifications.

Prefer existing source and bounded commit/file fetches. The cherry-picking skill's
`fetch-patch.py` supports authenticated GitHub requests and trial application in a
worktree. A raw `git apply --check` checks applicability to the selected working
tree; it does not preserve commit authorship or evaluate build dependencies.

For each change, establish module definitions, namespaces, interface versions,
partition placement, generated outputs and manifest ownership. Static preflight
scans are supplemental; they do not evaluate the full Make/Soong graph.

When publishing is authorized, order repositories by their actual dependency graph.
Publish a dependency before a manifest or consumer points to its new revision.
Hardware → vendor → device is an example, not a universal order. Verify remote
SHAs and the resulting manifest selection; a push alone does not change a build
whose manifest still selects another repository or revision.
