# Cherry-pick / port playbook

## 1. Find

- Where the change lives and how to fetch it: `sources.md`.
- Prefer sources on the same Android version and CLO tag (LineageOS device/HAL repos, AOSPA,
  CLO-based ROMs). Verify every external framework/vendor dependency against the
  actual target; a shared Android version does not guarantee the same APIs.
- Search by path first (`gh api 'repos/O/R/commits?sha=BR&path=P&per_page=30'`), then by subject.
  GitHub commit search covers default branches only.

## 2. Vet before fetching

1. `python3 scripts/followups.py O/R SHA --branch BR` finds possible follow-ups in a
   bounded path/date scope. Read relevant diffs: a REVERT needs its rationale reviewed,
   and a FIX or MENTION is a candidate, not an automatic dependency. Search broader
   history when renames, timestamps or omitted paths leave uncertainty.
2. Read the whole diff. List everything it needs that it does not add: classes/methods, soong
   modules and AIDL versions (`android.hardware.light-V3-rust`), sepolicy types and macros, props,
   resources, files, kernel configs.
3. Confirm each exists in our tree: `git grep` in a local clone, or for big repos
   `gh api 'repos/OURS/R/contents/PATH?ref=BR'`. If something is missing, port it first or drop
   the pick.
4. Check for version skew: API level, AIDL/HIDL version, renamed modules, moved files,
   Kotlin/Java mix.

## 3. Fetch and trial

```sh
python3 scripts/fetch-patch.py REF [REF...] -C OUR_REPO --check
# relocate a directory and keep only part of a series
python3 scripts/fetch-patch.py O/R@A..B --include 'aidl/lights/*' --map aidl/lights/=lights/ -C OUR_REPO --check
```

The check runs `git am -3` in a throwaway worktree of `OUR_REPO` HEAD and names the failing patch
and files.

## 4. Apply

| Situation | Do |
|---|---|
| Applies cleanly | `fetch-patch.py ... -C REPO --am` (author kept), or `git cherry-pick -x SHA` when the source is fetched into the clone |
| Same code, different directory | `--map old/=new/` (one command per series) |
| Only part of a commit applies | `--include` / `--exclude`, then credit as an adapted port |
| Conflicts | Resolve to intent: read upstream's file at the commit's parent and ours. Never drop our local fixes. Re-run checks |
| Shallow or partial clone (`-3` cannot find preimage blobs) | `git am` without `-3`, or `git apply --reject` and fix the `.rej` hunks |
| Needs an earlier upstream commit | Pick that first. Find it with `followups.py` or a path log ending at the commit date |
| Different design on our side | Hand-port the minimal equivalent. Upstream author if it's their change; credit per `credit.md` |

Prefer the existing local clone and bounded patch fetches for large repositories.
Fetch missing objects only when needed and within the task's resource constraints.

## 5. Credit

`python3 scripts/credit.py O/R SHA [SHA...]` (or `--mirror`). Rules: `credit.md`. Keep the
upstream subject when the change is the same; later syncs then recognise it as already picked.

## 6. Verify and record; publish when authorized

- `preflight.py` for device trees (`build-safety.md` for the rest).
- Re-read `git show` for every new commit: identity, credit, message style.
- When publication is authorized, push in the actual dependency order and verify remote tips.
- If the source is a tracked upstream, add a sync-log entry in the device skill.
