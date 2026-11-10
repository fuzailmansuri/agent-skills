# History surgery — how to do it without wrecking anything

Context: a fork's commit list has drifted — many tiny chatter commits, name variants of the
same author, enable/revert pairs netting zero, missing co-author trailers. This is a valid
cleanup, but one bad step loses authorship or content. The method below survived multiple
large multi-hundred-commit rewrites with byte-identical trees.

## 0. Preconditions
- Backup branch (`backup/pre-<what>`), never pushed.
- Record the final tree: `git rev-parse HEAD^{tree}` — surgery must end with this exact SHA.
- Rewriting history on a pushed branch is an **explicitly authorized action**; suggest
  `--force-with-lease=refs/heads/BR:REVIEWED_SHA` for the reviewed destination.
  Existing authorization persists; do not ask again for the same approved scope.

## 1. Classify before touching
Run an author census (`git log --format='%an <%ae>' | sort | uniq -c | sort -rn`): reveals
name variants of one author. Map every variant to ONE identity; decide this **before**
anything (on git-identity grounds: commit-normalize by EMAIL, not by guessing display
names).

## 2. Structural passes (order matters)
1. **Identity normalization** via `git filter-branch --env-filter` keyed on email:
   `if [ "$GIT_AUTHOR_EMAIL" = "who@host" ]; then export GIT_AUTHOR_NAME="..." ; fi`.
2. **Net-zero pair deletion.** Verify pairs at the PATCH level: `git show A` vs `git show B`
   — exact inverse hunks, or `tree(A^) == tree(B)` **only if B is A's child**. Never compare
   trees of commits far apart (intervening commits make the trees differ even when the pair
   is neutral).
3. **Squash consolidation.** Only squash commits that are **adjacent in history**. `fixup`
   into the base keeps its author; substitute a dense topic message via
   `exec git commit --amend -F msgfile`. Squashing adjacent commits is tree-safe at every
   boundary (the merged commit's tree equals the original last member's tree) — reordering
   across unrelated authors is NOT; avoid it without conflict budget.
4. **Trailer injection** via `--msg-filter` gated on the (normalized) author name, and only
   when a co-author trailer is absent (grep the message first to avoid duplicates).

## 3. Practical traps that cost real time
- A `GIT_SEQUENCE_EDITOR` script does not receive the todo on stdin; it receives its **file path as
  argv[1]** and must WRITE that file. A script that prints to stdout merges nothing
  ("nothing to do" is the symptom).
- `filter-branch --msg-filter` sees the (env-normalized) `GIT_AUTHOR_NAME` when both filters
  run in the same invocation — use that rather than re-querying git.
- Appending to a message: `msg=$(cat); printf '%s\n\nCo-authored-by: ...' "$msg"` — the
  message already ends with a newline.
- `filter-branch` leaves `refs/original/*` — inspect, then delete.
- After each pass: `git rev-parse HEAD^{tree}` must equal the recorded value; run the author
  census again; spot-check the squashed subjects.

## 4. Push
Publish once after verifying the approved rewrite, with a lease pinned to the
reviewed remote SHA. If the lease fails, inspect the moved branch; do not retry with
unconditional force. Never interleave pushes between passes.

## 5. Splitting a bulk "import" commit into proper history

A single commit that dumps dozens of files ("Import adaptations from X", many co-author
lines) hides authorship and shows nothing a reviewer can read. Split it:

1. **Find the sources.** Save the candidate upstream commits as patches (`fetch-patch.py`,
   one file per commit) into a scratch dir.
2. **Measure.** `python3 scripts/hunk-coverage.py COMMIT PATCH_DIR -C REPO` lists which
   upstream commits explain how many of the commit's added lines, and what is left over.
   Overlapping lines are candidates, not proof of provenance. Verify the full changes,
   source revisions and author metadata before attributing or replaying them.
3. **Replay upstream-explained parts** as separate commits: upstream author and date kept
   (`git commit --author=... --date=...`), upstream subject, body with the source URL or a
   `(cherry picked from commit SHA)` line, then `Signed-off-by: <you>`. Assign each upstream
   commit **once**; a second stage that replays an already-assigned commit duplicates it
   (check `git log --format=%s | sort | uniq -d` before pushing).
4. **Group the leftover** into your own topical commits (one subsystem per commit: avb,
   sepolicy, overlays, props...), short subject and `* ` bullets, you as author.
5. **Preserve content during history-only work.** Potentially unused entries are
   separate functional changes. Prove their consumer scope and review them separately;
   do not silently delete them during an authorship or commit-structure cleanup.
6. **Handle Gerrit `Change-Id:` for the destination.** Retain it when continuing
   the same review; avoid reusing it for an unrelated change.
7. **Verify.** For history-only work, the final tree equals the recorded tree.
   Review authorship and provenance as well as content. A static preflight scan does
   not replace this equality check.

Do the work in a throwaway `git worktree` on a new branch so a running build in the main
checkout is untouched; the user later runs `git reset --hard <remote>/<branch>` themselves.

## 6. More traps
- **Shallow clones:** commits at the shallow boundary cannot be rewritten (the branch would be
  orphaned). `git fetch --deepen N` only in the repo being rewritten, never a big one.
- **Ambiguous cleanup wording.** "Delete the commits" can mean drop the feature or only tidy
  the history. Ask which; if a feature was dropped by mistake, restore it and remove the
  drop/revert pair instead.
- **Global identity leaking.** A machine-wide `user.name` that belongs to someone else turns
  into wrong authorship across a whole session. Set `user.name`/`user.email` per repo before
  the first commit, and census authors after the work (`git log --format='%an <%ae>'`).
- Re-authoring is for work that is solely the user's. Verbatim ports of someone else's code
  keep that author (see `credit.md`).
