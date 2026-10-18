# Syncing a maintainer's pushes (device / vendor / hardware)

Pattern: someone upstream (e.g. the device tree's active maintainer) pushes to their device tree, vendor
repo and hardware repo; our forks have diverged; take what helps, skip what can't build.

## 1. Start from the checkpoint

The device skill keeps a sync log with the last reviewed upstream SHA per repo. Use it as `-s`,
so only new commits get reviewed. What moved: `gh api 'users/U/repos?sort=pushed&per_page=10'`.

## 2. Small repos (device tree, hardware/*, packages)

```sh
bash scripts/upstream-diff.sh -C ~/android_device_X -u UPSTREAM_REMOTE -b BR -f origin/OURS -s CHECKPOINT -p device/OEM/X
```

- **HAVE**: same patch, same subject, or a no-op on our tree. Skip.
- **CLEAN**: applies. Pick it if every repo named in its `refs:` is in our manifest.
- **CONFLICT**: read both sides. Hand-port only if it stands alone.
- **refs: path we lack** (e.g. `hardware/nothing2`): it depends on their other repos. Port the
  dependency first (as with the lights HAL) or skip it.

Before calling something "missing", diff the trees: `git diff origin/OURS usync/BR -- PATH`.
Upstream often re-imports our own work under new subjects, and commits show up as missing when
the content is already there.

## 3. Vendor repos (huge: never clone)

- A vendor repo is an extract of one device tree's `proprietary-*.txt`. Never take their vendor
  without their device tree.
- Compare: `python3 scripts/vendor-tree-diff.py THEM/R@BR US/R@BR`. Net list changes:
  `bash scripts/blob-drops.sh -C DT_CLONE OLD NEW origin/OURS`. Line diffs of lists exaggerate.
- Change ours: `python3 scripts/vendor-api-commit.py --repo US/R --branch BR --drop-module M --drop-file P`.
  Dry run first; `--apply` fast-forwards only. Drop the device-tree list lines in the same
  change set.

## 4. Their hardware repo has a different layout

Relocate with `fetch-patch.py THEM/R@A..B --include 'their/dir/*' --map their/dir/=our/dir/ -C OUR_HW --am`.
Rewrite sepolicy and makefile glue by hand into our layout and credit it as an adapted port.
Never duplicate a type the device tree already declares; `preflight.py` catches that.

## 5. Push and record

1. `preflight.py --dt DT --hw HW --vendor US/VENDOR@BR` shows 0 errors.
2. Push hardware, then vendor, then device tree. Fast-forward; check each tip through the API.
3. Add a sync-log row in the device skill: date, upstream repo@branch, reviewed-up-to SHA,
   picked (our SHAs), skipped with reasons.
4. Tell the user what to check on the device, and any RE leads found along the way.
