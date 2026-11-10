---
name: read-android-source
description: >-
  Locate and explain upstream Android implementations in AOSP, Qualcomm CodeLinaro,
  LineageOS and ROM mirrors. Use for source-backed behavior questions, callers and
  configuration, version or tag comparisons, and device-tree cross-checks without
  cloning large repositories.
---

# Read upstream Android source

Answer against a specific repository and revision. Read
[android-tree-map.md](references/android-tree-map.md) when locating an unfamiliar
subsystem; treat its paths and tag families as starting points to verify.

## Engineering standard

Do not answer from remembered AOSP behavior when the target branch can be read.
Verify every API, symbol, property and path before relying on it. A source
implementation is not proof that the device builds, selects or executes it.

Distinguish observations, inferences and unknowns. Admit missing source, access,
tools or knowledge directly; a failed fetch does not mean the implementation is
absent. Never fabricate citations or pretend to have inspected unavailable code.
Correct a mistaken assumption explicitly and revisit conclusions built on it.
Prefer explaining the actual platform contract to proposing a clever workaround.

## Sources

| Host | Read and search | Limits |
|---|---|---|
| cs.android.com | Symbol/file search, references and history | Check the selected project and branch; an index is a locator, not complete evidence for every release. |
| android.googlesource.com | `PROJECT/+/REF/PATH?format=TEXT` for base64 file contents; `?format=JSON` for metadata/listings; `+log/REF/PATH?format=JSON` for history | Strip the Gitiles anti-XSSI prefix before parsing JSON. Access failures require another source or an explicit gap. |
| git.codelinaro.org | GitLab project API and `/-/raw/REF/PATH` where available | Verify current project location, access and exact platform/tag family; host or mirror migrations can invalidate old URLs. |
| review.lineageos.org | Gerrit changes by project/path, revision metadata and patches | An open review is not a merged implementation; pin the patchset or merged commit. |
| GitHub mirrors | `gh api` commit/tree/content endpoints and code search | Code search indexes the default branch. Resolve and inspect the requested branch separately. Mirrors may lag upstream. |

Prefer an existing local checkout when it matches the question. Use bounded file,
commit and path-history requests before considering a large fetch. Paginate history
when claiming coverage; report limited searches as limited.

## Method

1. Establish the Android base, device/vendor context, repository and branch/tag.
   Resolve moving refs to commit SHAs for comparison and citations.
2. Locate the implementation using the appropriate source index or a scoped `rg`.
   Open the actual code at the selected revision, including relevant declarations.
3. Trace callers, build selection, feature flags, overlays, init/property writers
   and vendor overrides that can change the effective behavior.
4. For version questions, compare pinned revisions and inspect relevant commits;
   distinguish first appearance in the searched history from a proven introduction.
5. Report the mechanism with repository, SHA and path/line links. Explain what
   source proves and what still needs a build or device observation.

CLO tags are repository/platform specific; equal-looking tag numbers in QSSI,
VENDOR and kernel projects do not establish a matched release. A sibling-device
implementation is a lead until hardware, firmware and interface contracts match.

For fetching and adapting patches, use `reverse-engineering-cherry-picking` when
available; ordinary source reading does not require its scripts or a REA server.
