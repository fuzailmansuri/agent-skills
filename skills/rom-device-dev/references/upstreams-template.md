# Upstream map & sync log — public template

This template is intentionally free of any real names or device specifics. Keep the real
fork map and running sync log in `_personal/` (gitignored), using the same column layout.

## 1. Fork map & push targets (template)

| Local path | Your fork | Branch | Notes |
|---|---|---|---|
| `device/<vendor>/<codename>` | `<you>/device_<vendor>_<codename>` | `<main-branch>` | Patch-level sync remotes; work in worktrees. |
| `vendor/<vendor>/<codename>` | `<you>/vendor_<vendor>_<codename>` | `<main-branch>` | Large — never clone whole; compare via `vendor-tree-diff.py`. Check the fork's parent — it may not be the repo you expect. |
| `hardware/<vendor>` | `<you>/hardware_<vendor>` | `<main-branch>` | Note layout differences from upstream's platform_hardware layout; `--map` paths when porting. |
| `kernel/...` | `<you>/kernel_<soc>` | `<kernel-branch>` | Modules/devicetrees often separate repos. |

Manifests live in `<you>/android-manifest@<branch>` (locals + patches) with a separate
manifest branch per ROM experiment.

## 2. Upstream maintainers (template)

| Repo | Branch | Notes |
|---|---|---|
| `<maintainer>/device_<vendor>_<codename>` | `<their-branch>` | Active line; compare `upstream-diff.sh` before every sync. |
| `<maintainer>/platform_hardware_<vendor>` | `<their-branch>` | Upstream's layout may differ from yours; use `fetch-patch.py --map old/=new/`. |

## 3. Sync log (append per session, newest first)

| Date | Upstream repo@branch | Reviewed up to (SHA) | Picked (our SHAs, credit) | Skipped (why) |
|---|---|---|---|---|
| YYYY-MM-DD | `<owner>/<repo>@<branch>` | `<SHA>` | `<sha>` as `<ours>` (author credit) | already-have / different layout / needs missing dep |

## 4. Open leads (append per RE session)

Short bullets with why-it-matters: which blob/HAL/prop a feature touches, what the OSS side
does not implement, and where to verify after the next build. Same rules: placeholder names
for anything non-generic; the real names live in `_personal/`.
