---
name: reverse-engineering-cherry-picking
description: >-
  Reverse engineering and cherry-picking for Android ROM and device bring-up work. Use when the user
  wants to find out how a stock blob, HAL, APK, kernel module, firmware or the live device does
  something; to turn SELinux denials into policy; or to pick, port, sync or adapt commits from another
  ROM, kernel, AOSP/CLO or device maintainer (GitHub, GitLab/CodeLinaro, googlesource, Gerrit,
  kernel.org) into their own trees, build-safe without a build, without cloning big repos, and with
  upstream credit. Triggers: "reverse engineer", "what does this blob/HAL do", "decompile", "avc
  denials", "cherry-pick", "pick from AOSPA/Lineage/CLO", "port this HAL", "<maintainer> pushed, sync",
  "what did upstream drop".
---

# Reverse engineering & cherry-picking

Two halves of one job: find out what something really does (RE), then bring the right change
into our trees (pick or port) without breaking a build nobody is going to run.

Scripts are in `scripts/` (Python 3 stdlib, git, authenticated `gh`; nothing else). Run them
from this skill's folder as `python3 scripts/X.py` or `bash scripts/X.sh`; every one has `-h`.

## Ground rules

1. **Identity.** Commit as the user's own configured git identity (`git config user.name` /
   `user.email`). Verify before every commit; never a work or default identity.
2. **Credit upstream.** Picks keep the upstream author. Adapted ports: upstream author as author,
   cite the source commit URL, `Co-authored-by` + `Signed-off-by` for the porter. Our own follow-up
   to their change: the porter as author, `Co-authored-by: <them>`. `scripts/credit.py` prints it;
   rules and examples in `references/credit.md`. Forked third-party skills are attributed fully —
   see `references/credit-policy.md`.
3. **Messages.** Technical only. No AI attribution trailers, never mention Apple/iOS or
   "inspired by".
4. **Hands off other people's repos.** No PRs, issues or comments upstream unless the user names
   the repo. Push only to repositories the user controls.
5. **No builds.** Nothing gets built to test. A change must be right by inspection plus
   `scripts/preflight.py`. Never pick code that needs something the target tree lacks.
6. **No big fetches.** Never clone a vendor repo or pull a large history: single patches via
   `fetch-patch.py`, trees via the API, vendor edits via `vendor-api-commit.py`.
7. **Work on copies.** Trial picks in throwaway worktrees. Never rewrite a pushed branch unless
   asked; then `--force-with-lease` only.

## Pick the playbook

| Task | Read |
|---|---|
| What does blob / HAL / app / node X do? Why is feature Y broken? | `references/reverse-engineering.md` |
| SELinux denials to policy | `scripts/avc2rules.py --live --no-apps`, then the sepolicy part of the RE playbook |
| Pick or port commits from another ROM, kernel, AOSP, CLO | `references/cherry-pick.md` |
| A maintainer pushed device/vendor/hardware changes: sync them | `references/upstream-sync.md` |
| How to fetch from GitHub, GitLab, googlesource, Gerrit, cgit | `references/sources.md` |
| Will this tree still build? | `references/build-safety.md` + `scripts/preflight.py` |
| Shell, git and Termux gotchas | `references/pitfalls.md` |

Device facts (repo map, upstreams, sync checkpoints, open leads) live in the device skill for
the target device if one exists (e.g. the `rom-device-dev` runbook plus its private `_personal/`
notes). Load it alongside this one.

## Tools

| Script | What it does |
|---|---|
| `fetch-patch.py` | Commit, range, PR or Gerrit change from any host to an mbox for `git am`; `--map old/=new/` relocates files, `--include/--exclude` filter, `-C REPO --check` trial-applies, `--am` applies |
| `followups.py` | Later reverts, fixes and touches of a commit upstream. Run before every pick |
| `credit.py` | Author and trailers for a port (`--mirror` for our follow-ups) |
| `upstream-diff.sh` | Upstream branch vs our fork: HAVE / CLEAN / CONFLICT per commit, plus the other repos each commit references |
| `blob-drops.sh` | Net proprietary-list changes between revisions (reorders ignored), marks what our fork ships |
| `vendor-tree-diff.py` | Two vendor repos compared through the API, no clone |
| `vendor-api-commit.py` | Drop modules/files or upload blobs in a vendor repo through the API. Dry run by default; refuses a drop another module still needs |
| `preflight.py` | Static build checks: vendor makefiles, sepolicy duplicates and conflicts, duplicate VINTF HALs, init services, undefined device modules, list drift |
| `blob-intel.py` | ELF RE without binutils: needed libs, exports, AIDL/HIDL interfaces, sysfs/dev nodes, props, paths, behaviour from imports; `--dir` for who-needs/missing/orphans; `--su` reads live `/vendor` |
| `avc2rules.py` | Denials to `allow` / `set_prop` / `binder_call`, flags "label first" and neverallow risks; `--live` reads this device |

## The loop

**Reverse engineering**
1. Write the question down: which node, prop, service, library, or why denied.
2. Get the artifact: live device through `su -c`, a stock dump, the vendor repo, the APK.
3. Native: `blob-intel.py`; Java: jadx/apktool/aapt2; behaviour: `strace`; denials: `avc2rules.py`.
4. Confirm on the device (read the node, `getprop`, `logcat`) before writing code.
5. Record what was learned in the device skill when it will matter again.

**Cherry-pick / port**
1. Find it (`references/sources.md`). Prefer sources on the same Android base and CLO tag.
2. Vet it: `followups.py`, read the whole diff, list everything it needs (symbols, modules, types,
   props, files, AIDL versions) and confirm each exists in our tree.
3. Fetch and trial: `fetch-patch.py REF [--map ...] -C OUR_REPO --check`.
4. Apply: `--am` (author kept) or `git cherry-pick -x` when the source is local. Adapt by hand
   when layouts differ, then credit per `references/credit.md`.
5. Verify: `preflight.py`, re-read the final diff.
6. Push dependencies first (hardware, then vendor, then device), fast-forward only.

## Report back

- Per repo: new SHA, one line on what and why.
- Skipped items, each with its reason (missing dependency, already have, reverted upstream).
- What to check on the device (log tags, `ps -A | grep`, avc), and the upstream commit URLs.
