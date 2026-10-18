# Repositories, manifests & fast patching workflow

## 1. Manifest & branch architecture (template)

A ROM build is governed by one manifest repo:
- **ROM manifest:** `<rom-org>/manifest@<branch>` — the daily-driver base.
- **Local manifests & patchsets:** your own `<you>/android-manifest@<branch>` with
  `patches/` and repo overrides for every customized component (device, hardware, vendor,
  kernel, frameworks, LaunCher).
- **Sandbox / experiment branches:** kept as branches across the *entire* repo set (device,
  frameworks, vendor, manifest), never mixed into the daily branch.

Keep each component in its own fork; localize only the repos that deviate from upstream, so
the manifest diff is the inventory of your customizations.

## 2. Fast patching (no big fetches)

Fetching whole repo histories (frameworks/base is many GB) consumes device storage and
mobile bandwidth. Patch-level paths:

```bash
gh api repos/<owner>/<repo>/commits?per_page=10                     # list
curl -s -H "Accept: application/vnd.github.patch" \
  https://api.github.com/repos/<owner>/<repo>/commits/<sha>  > /tmp/p.patch
git apply --check /tmp/p.patch && git apply --3way /tmp/p.patch      # index-only pre-checks
```
`fetch-patch.py` (cherry-picking skill) handles this for GitHub, GitLab/CodeLinaro,
googlesource, Gerrit and kernel.org, with path mapping and trial-apply into a worktree.

## 3. Verification without builds

- Inspect imports, method signatures and symbol presence against the target branch **before**
  applying: unresolved symbols or missing proprietary dependencies are the most common
  silent breakage.
- Run `scripts/preflight.py` (cherry-picking skill): duplicate VINTF HALs, SEP duplicates,
  init services without domains, undefined PRODUCT modules, list drift.
- Recheck every `sepolicy` addition: one rule per denial, minimal grants.

## 4. Push ordering
Dependencies push first (hardware → vendor → device), fast-forward only; the device tree
pulls the last so the parent repos exist in the manifest before it references them.
