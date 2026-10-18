# History surgery — how to do it without wrecking anything

Context: a fork's commit list has drifted — many tiny chatter commits, name variants of the
same author, enable/revert pairs netting zero, missing co-author trailers. This is a valid
cleanup, but one bad step loses authorship or content. The method below survived multiple
large multi-hundred-commit rewrites with byte-identical trees.

## 0. Preconditions
- Backup branch (`backup/pre-<what>`), never pushed.
- Record the final tree: `git rev-parse HEAD^{tree}` — surgery must end with this exact SHA.
- Rewriting history on a pushed branch is an **explicit fresh instruction**; suggest
  `--force-with-lease`, and remind the user the whole commits page changes.

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
- A `GIT_SEQUENCE_EDITOR` script reads **stdin** — it receives the todo **file path as
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
One flat force per approved rewrite (`git push --force` or `--force-with-lease`). Never
interleave pushes between passes.
