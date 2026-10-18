# Where commits live and how to fetch them without cloning

`scripts/fetch-patch.py` understands every URL form below. These are the raw recipes for
listing, searching and reading single files.

## GitHub (gh api, private repos work)

| Need | Command |
|---|---|
| One commit as a patch | `gh api repos/O/R/commits/SHA -H 'Accept: application/vnd.github.patch'` |
| Range or PR as a series | `.../compare/A...B` or `.../pulls/N`, same Accept header |
| Commits touching a path | `gh api 'repos/O/R/commits?sha=BR&path=P&since=ISO&per_page=100'` |
| A file at a ref | `gh api 'repos/O/R/contents/P?ref=BR' -H 'Accept: application/vnd.github.raw'` |
| Whole tree listing | `gh api 'repos/O/R/git/trees/BR?recursive=1'` |
| What someone pushed lately | `gh api 'users/U/repos?sort=pushed&per_page=10'` |
| Code search | `gh search code 'SYMBOL repo:O/R'` (default branch only) |

Cross-repo compare (`ours...them:branch`) only works inside one fork network. Otherwise it
returns 404; compare trees (`vendor-tree-diff.py`) or patches instead.

## GitLab, CodeLinaro (git.codelinaro.org), other GitLab hosts

- Patch: `https://HOST/GROUP/PROJECT/-/commit/SHA.patch`, MR: `/-/merge_requests/N.patch`.
- List: `https://HOST/api/v4/projects/GROUP%2FPROJECT/repository/commits?ref_name=BR&path=P`.
- Raw file: `https://HOST/GROUP/PROJECT/-/raw/REF/PATH`.
- CLO kernel and vendor trees: `git.codelinaro.org/clo/la/...`. Use tags matching our base (`LA.VENDOR...`).
- gitlab.com sometimes times out; retry before concluding anything.

## googlesource (android, chromium, kernel/common)

- Commit JSON: `https://android.googlesource.com/PROJECT/+/SHA?format=JSON` (strip the `)]}'` first line).
- Diff: `.../+/SHA%5E%21/?format=TEXT` (base64).
- Branch tip: `.../+/refs/heads/BR?format=JSON`. Walk `parents` from there; `+log` with a path
  can answer 401 to anonymous clients.
- Raw file: `.../+/REF/PATH?format=TEXT` (base64).
- ACK kernel: `android.googlesource.com/kernel/common`, branches like `android15-6.6`.

## Gerrit (review.lineageos.org, android-review.googlesource.com, ...)

- Search: `https://HOST/changes/?q=project:P+status:merged+file:PATH&n=25` (XSSI prefix).
- Patch: `https://HOST/changes/N/revisions/current/patch` (base64 of a format-patch).
- Metadata: `.../revisions/current/commit`.
- Open (unmerged) changes are fine to read. Treat them as unreviewed code.

## kernel.org

- cgit: `/commit/?id=SHA` becomes `/patch/?id=SHA`. Search: `/log/?h=BR&qt=grep&q=TEXT`.
- Mailing-list patches: `https://lore.kernel.org/all/MSGID/raw`.

## Common GitHub orgs for Android picks

LineageOS (device/HAL/sepolicy), AOSPA (QTI-heavy, CLO based), yaap (our base), crdroidandroid,
PixelOS-AOSP, Evolution-X, and the active device-tree maintainers for your device. Check
the org exists before citing it. Org names change; a fork's parent may surprise you
(`gh repo view --json parent`).
