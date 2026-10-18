# Parallel trees — same device, different maintainers

Long-lived device forks of the same tree drift apart: two branches of one device tree can sit
at DIFFERENT bases with hundreds of commits that "correspond" but never match. Sync between
them is curation, never a blanket merge.

## 1. Quantify the gap first
- Count commits on each side since the split (`git rev-list --count OLD..NEW`).
- `git cherry <target> <source>` gives exact patch-id matches (`-` = present). Patch-id noise
  is high after any squash/rewrite — treat `-` only as seeds, not the answer.
- Fuzzy subject matching (normalize punctuation/ordering, compare token overlap) catches
  their rewordings, but beware false "missing": a feature may exist in many small commits on
  one side and one squash on the other.

## 2. Curate, don't dump
For each candidate commit ask: (a) does the change depend on services/blobs/tunables that
exist on the target's base? (b) does it change behaviour the target already decided
differently (perf hints, zram, doze, power HAL interplay)? (c) is it a fix-class commit
(correctness) vs state-of-the-tree state (tuning)? **Fix-class** commits from the source are
usually portable; state commits mostly are not.

Rule of thumb, learned the hard way: on a fork where 340-odd commits sat unmatched, the
worthwhile set was a handful — a crash fix, a label, an overt tuning cleanup whose target
offered nothing equivalent. The rest was base.

## 3. Ship as cherry-picks with original authorship
`git cherry-pick` per commit (original author preserved), base first; conflicts resolve
against the target's semantics (if the target has both `enabled` and a comment about why,
that design wins over the移植 commit's "disable" — confirm with the user, don't silently
overwrite). Verify commit-by-commit with a per-commit diff review at the end — preflight.py,
then run the target tree like normal code.
