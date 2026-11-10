---
name: reverse-engineering-cherry-picking
description: >-
  Investigate Android blobs, HALs, firmware and SELinux failures, or cherry-pick,
  adapt and synchronize upstream changes into ROM and kernel trees. Use for
  artifact-backed diagnosis, dependency-aware ports, upstream review and requested
  Git history repair. Includes bounded fetches and static checks when builds are unavailable.
---

# Android investigation and upstream integration

Establish what the target does, then bring in the smallest justified change with
its original authorship. Applicability alone does not establish correctness.

## Evidence and judgment

- Think like an AOSP engineer: pin the branch and artifact, read the implementation
  and callers, trace the interface contract, and verify dependencies in the target.
  Prefer an existing platform mechanism over a clever workaround or invented API.
- State facts, inferences and unknowns separately when they affect the decision.
  Strings and imports suggest possible behavior; they do not prove execution.
  Commit subjects and patch similarity are search aids, not current-tree parity.
- Never fabricate an API, symbol, log, command result, test, provenance or certainty.
  Be direct about missing hardware, source, tools, access or knowledge. If evidence
  is insufficient, say so and identify the smallest check that would resolve it.
- Challenge a bad assumption with technical evidence. If your own assumption was
  wrong, acknowledge it and recheck dependent changes. Do not cover a knowledge
  gap with confident wording, speculative tuning or broad permission grants.
- Report what validation actually establishes. Static checks cannot prove a build,
  boot, ABI compatibility, performance improvement or fixed runtime behavior.

## Scope and repository conventions

Inspect target repository state, manifest selection, source and destination refs,
local changes and the task's constraints. Use a throwaway worktree for trial picks.
Use configured target-repo identity as committer; preserve upstream authors, dates
and source URLs. Technical messages, human credit, no AI trailers.

Prefer existing clones and file/commit APIs over large history downloads, especially
on constrained hosts. Respect explicit no-build instructions; otherwise use the
checks appropriate to the task and available environment. Do not assume the host
is a rooted phone. Scripts using `--live` or `--su` execute on the local host.

Do not infer publishing or history-rewrite authority from a local edit. Honor
existing authorization without repeatedly asking; verify the authorized repository
and branch before writing. Published-history rewrites need explicit authorization,
a backup and a lease pinned to the reviewed remote SHA. No unrequested upstream
PRs, issues or comments. Keep private device maps and logs outside tracked skill text.

## Choose a playbook

| Task | Read |
|---|---|
| Artifact or runtime investigation, SELinux diagnosis | [reverse-engineering.md](references/reverse-engineering.md) |
| Pick or adapt commits across Android bases | [cherry-pick.md](references/cherry-pick.md) |
| Review a maintainer's new commits | [upstream-sync.md](references/upstream-sync.md) |
| Compare divergent device forks | [parallel-trees.md](references/parallel-trees.md) |
| Fetch from GitHub, GitLab/CLO, Gitiles, Gerrit or cgit | [sources.md](references/sources.md) |
| Static validation and its limits | [build-safety.md](references/build-safety.md) |
| Authorship and provenance | [credit.md](references/credit.md) |
| Requested history cleanup | [history-surgery.md](references/history-surgery.md) |
| Shell, Git and Termux pitfalls | [pitfalls.md](references/pitfalls.md) |
| Vendored-skill attribution | [credit-policy.md](references/credit-policy.md) |

## Tools

Run scripts from this skill's directory; every script supports `-h`. Python scripts
use the standard library. Shell scripts need Bash (upstream-diff needs Bash 4+).
GitHub operations require `gh` and appropriate access. Local static scans do not.

| Script | Purpose and limits |
|---|---|
| `fetch-patch.py` | Fetch mbox patches; optionally filter/map paths, trial `git am` in a worktree, or apply to the selected repo. Path transformations reject unsupported quoted paths. |
| `followups.py` | Paginated path/date search for possible follow-ups on a pinned GitHub branch tip. Signals require review; renamed paths and older-dated commits can escape it. |
| `upstream-diff.sh` | Cumulative trial picks: HAVE means a no-op at that trial state, CLEAN means applicable, CONFLICT needs inspection. Merges are skipped and require separate review. |
| `hunk-coverage.py` | Added-line overlap between a bulk commit and candidate patches; not proof of semantic equivalence or authorship. |
| `credit.py` | Format author/source/trailer information from upstream metadata. |
| `blob-drops.sh` | Net list-entry additions/removals; strips flags and hashes, so review those changes separately. |
| `vendor-tree-diff.py` | Compare vendor tree objects through GitHub without cloning. |
| `vendor-api-commit.py` | Dry-run vendor module/file changes; `--apply` creates a commit and fast-forwards the branch. Checks a supported generated-file layout, not the complete Soong graph. |
| `preflight.py` | Heuristic modules, vendor files, policy, VINTF and init checks over supplied roots. Read its warnings and unverified scope. |
| `blob-intel.py` | ELF dependencies, symbols and strings; possible consumers and missing dependencies within the supplied dump. |
| `avc2rules.py` | Group AVCs and propose policy candidates; label-first and risk notes do not establish a valid policy. |

## Working loop

1. Identify the question, artifact/revision and target contract. Gather evidence before editing.
2. Review candidate diffs and possible follow-ups. Verify symbols, modules, interface
   versions, policy, configuration and runtime consumers against the target.
3. Trial the series in dependency order. Investigate conflicts and no-ops against
   current content; do not skip a change because a similar title appears in history.
4. Apply or adapt within scope, preserving local behavior and upstream credit.
5. Review final diffs, run applicable checks, and state unresolved build/runtime gaps.
6. If publication is authorized, publish in the actual dependency order and verify
   destination refs. Record reviewed upstream SHAs, picks, skips and their reasons.

Report the change, source evidence, checks and remaining limitations plainly.
Use `rom-device-dev` when available for device integration and private device notes;
this skill's investigation and import workflow also works without that companion.
