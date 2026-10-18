---
name: read-android-source
description: >-
  Read and navigate upstream Android source online without cloning: Google AOSP
  (android.googlesource.com / cs.android.com), Qualcomm CodeLinaro (git.codelinaro.org,
  LA.* tags), and LineageOS (review.lineageos.org, GitHub mirrors). Use when the user asks
  where something is implemented, what stock code does, which version/tag introduced or
  changed a behaviour, or wants to cross-check a device tree against Android/CAF source.
  For fetching single commits use the reverse-engineering-cherry-picking skill's
  fetch recipes; that is not this skill's focus.
---

# Reading upstream Android source (AOSP, CLO, LineageOS)

Answer "where is this / what does stock do / which tag has it" against the *real* trees.

## The tree map

Do not guess where code lives — check `references/android-tree-map.md` first: repo → concern
(frameworks/base, system/, hardware/interfaces, packages/services, vendor, build). The map
also lists CLO's LA. tag families and Lineage's repo/branch conventions.

## Reading tools (no clone)

| Host | Browse/search | Raw file | Notes |
|---|---|---|---|
| **cs.android.com** (AOSP code search incl. history) | query bar: `file:` / symbol search | opens the source directly | covers all AOSP branches + chromium cross-refs |
| **android.googlesource.com** | `+/refs/heads/BR?format=JSON` (branch/listing walks), `+log` per-path can 401 anonymously | `+/REF/PATH?format=TEXT` (base64) | authoritative AOSP; gitiles links `+-/blob` |
| **git.codelinaro.org** (Qualcomm CLO) | GitLab web + `api/v4/projects/GROUP%2FPROJECT/...` | `/-/raw/REF/PATH` | tags `LA.QSSI-*`, `LA.VENDOR-*`, `KERNEL.PLATFORM-*`; match the exact CLO family a build shipped with |
| **review.lineageos.org** (Lineage Gerrit) | `/changes/?q=project:P+file:PATH` | `/changes/N/revisions/current/patch` | merged + open history incl. device/HAL trees |
| **GitHub mirrors** (LineageOS org, aosp-mirror, device maintainers) | `gh api` / `gh search code` (default branch only) | `contents/PATH?ref=BR` | aosp-mirror is periodic, not authoritative |

Patch/commit fetch recipes (mbox generation, compare, tree diffs) live in the
`reverse-engineering-cherry-picking` skill → `references/sources.md`.

## Method

1. **Pin the target question**: which repo+file, which Android/CAF/Lineage version, whose
   device tree is the reference (read `references/android-tree-map.md` when unsure).
2. **Search breadth-first**: symbol or string through cs.android.com (AOSP), CLO GitLab
   (`search:` scope), Lineage Gerrit (`project:` + `file:`), GitHub mirrors (default-branch
   caveat). `grep` locally only after narrowing.
3. **Open the file raw** (base64 googlesource / GitLab raw / GitHub raw) and read the
   version at the closest tag/branch to the user's tree — reading HEAD when you care about
   an older base is the classic wrong-answer trap.
4. **Trace sideways**: who calls into it (cross-refs on cs.android.com), which overlay or
   build config flips the behaviour, and which device tree override would take precedence.
5. **Record what still needs testing** on a device: which prop, node, service, or HAL
   instance. The rom-device-dev skill keeps the device-log side.

## Pitfalls

- Googlesource gitiles `?format=JSON` needs the `)]}'` prefix stripped before `json.loads`.
- CLO tags are per-platform families; the SAME tag number varies across `LA.QSSI`,
  `LA.VENDOR` and kernel-led repos — always name repo+tag together.
- Lineage Gerrit "changes" search: open statuses differ from merged; treat open as
  unreviewed.
- GitHub code search only indexes the default branch — for history/branches use the API.
