# Pitfalls (each one cost time once)

## Termux / phone

- `/tmp` is not writable. Use `$TMPDIR` or `$PREFIX/tmp`.
- The interactive shell wraps `grep`, `find` and `sort` in functions, and some invocations fail
  with "error while loading shared libraries: -G/-S". Use `command grep` etc. (the scripts unset
  these).
- Some agent shells don't keep `cd` between calls. Use `git -C DIR` and absolute paths.
- `/vendor`, `/odm` and `/mnt/vendor` are unreadable as the app user. `su -c` (KernelSU) works
  non-interactively.
- Without termux-exec, `#!/usr/bin/env` shebangs fail ("bad interpreter"). Always run
  `bash x.sh` / `python3 x.py`.
- Pipelines with `set -o pipefail` die when a `grep` matches nothing. Wrap optional greps in
  `{ ...; } || true`.

## git / GitHub

- `git worktree add -b X PATH` creates branch X even when it then fails on an existing PATH.
  Delete the stray branch.
- `git config` inside a worktree writes the main repo's config.
- Cross-fork compare returns 404 outside one fork network. Check a fork's parent before
  assuming whose tree it follows (`gh repo view --json parent`) — vendor forks are frequently
  re-forked from a different maintainer's line than the one you know.
- GitHub commit/code search only covers default branches.
- `git am -3` needs the preimage blobs. Shallow clones can't provide them, so use plain `am` or
  `apply --reject`.
- Adapted commits have new patch-ids. Only the subject links them to upstream, so keep the
  upstream subject.
- `grep` on `proprietary-files.txt` diffs exaggerates: regens reorder sections. Use `blob-drops.sh`.

## Android trees

- `Android.bp` top-level blocks end at a column-0 `}`. Splitting on column-0 lines leaves stray
  braces. Use `vendor-api-commit.py`, which removes whole blocks and verifies the module set.
- Dropping a blob: also its `PRODUCT_PACKAGES` / `PRODUCT_COPY_FILES` lines, the list entries,
  every module that depends on it, and any unrelated triggers in its rc file.
- Two HALs declaring the same instance (QTI lights xml + OSS lights xml) fail VINTF assembly.
  `preflight.py` catches it.
- Pushing to a fork does nothing unless the manifest points at that fork and branch.
- Upstream re-imports our own work under new subjects. Diff the trees before calling anything
  missing.

## Hosts

- android.googlesource.com `+log` with a path can answer 401 to anonymous clients. `+/SHA` and
  `+/refs/heads/BR` work.
- gitlab.com occasionally times out. Retry once before concluding.

## History surgery

- Squash merges of adjacent commits keep the boundary trees; reordering does not. Verify
  adjacency with `git log --reverse` before generating a rebase todo.
- `git cherry` patch-ids break across squashes/rewrites — use them as seeds only.
- filter-branch leaves `refs/original/*` — delete after checking.
