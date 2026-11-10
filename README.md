# agent-skills

Reusable Android engineering skills for AI coding agents. One copy in this repo, linked into every
agent. Skills are written generically so they work on any device or ROM; personal
repo-specific notes belong in `_personal/` (gitignored, never published).

| Skill | What it covers | Credit |
|---|---|---|
| [`read-android-source`](skills/read-android-source/SKILL.md) | Reading upstream Android source online: AOSP, Qualcomm CodeLinaro (LA. tags), LineageOS, custom-ROM mirrors; the AOSP/CLO/Lineage tree map | original work, this repo's author |
| [`reverse-engineering-cherry-picking`](skills/reverse-engineering-cherry-picking/SKILL.md) | Android RE (blobs, HALs, APKs, firmware, live device, SELinux), cherry-picking/porting with credit, upstream sync, build-safety without builds, history surgery, parallel-tree sync | original work, this repo's author (including battle-tested case studies) |
| [`rom-device-dev`](skills/rom-device-dev/SKILL.md) | Android ROM device-tree bring-up and maintenance for any device/ROM: runbook rules, manifests, subsystem fixes, first-boot debugging, kernel-level work, integrity hygiene | original work, this repo's author |
| [`reverse-engineer-anything`](skills/reverse-engineer-anything/SKILL.md) | **Verbatim fork of [REA](https://github.com/morluto/rea)** (npm `rea-agents`) — native, managed, Electron/JS, packaged, firmware and browser RE with agents | **FULL credit to [REA](https://github.com/morluto/rea) and its authors** — see [`CREDITS.md`](skills/reverse-engineer-anything/CREDITS.md); synced to upstream `a4b4957` |
| [`ponytail`](skills/ponytail/SKILL.md) | **Verbatim copy of the core skill of [Ponytail](https://github.com/DietrichGebert/ponytail)** (MIT): the smallest change that fully solves the task | **FULL credit to [Ponytail](https://github.com/DietrichGebert/ponytail) and its author** — see [`CREDITS.md`](skills/ponytail/CREDITS.md) |

## Engineering standard

The original Android skills require source-backed reasoning: verify the target
branch and interface contract, separate facts from inferences, and admit missing
knowledge, access, tools or hardware. Agents must challenge unsupported fixes,
correct their own mistakes, and never fabricate APIs, evidence or successful tests.
Static review is reported as static review; compilation, boot, behavior and
performance need their own evidence. See the
[engineering-judgment guide](skills/rom-device-dev/references/engineering-judgment.md).

Vendored REA and Ponytail instructions remain upstream copies with their own scope.

## Install

```sh
git clone https://github.com/fuzailmansuri/agent-skills ~/agent-skills
bash ~/agent-skills/install.sh          # links skills into every agent found
bash ~/agent-skills/install.sh --list   # where each skill is linked
bash ~/agent-skills/install.sh --to /path/to/skills  # only this destination
```

| Agent | Where it reads skills |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenAI Codex CLI | `~/.agents/skills/` and `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Antigravity CLI | `~/.gemini/config/skills/` |
| Anything with SKILL.md | `bash install.sh --to DIR` |
| Agents without skills (Cursor, Aider...) | point them at `AGENTS.md` or open this repo |
| Chat-only models | paste `dist/<skill>.md` |

Update linked installations: `git -C ~/agent-skills pull --ff-only`. Run the installer
again when skills are added. Existing files, directories and links to other sources
are skipped unless `--force` is supplied; replacement creates a unique backup beside
the destination. `--remove` removes only this checkout's links. `--to DIR` now limits
all actions to the explicit destination (repeatable); it does not also install globally.
Copies installed by another tool need that tool's update workflow.

## Requirements for the scripts

Python 3.8+ (stdlib only) and Bash; `upstream-diff.sh` needs Bash 4+. Git operations
need `git` and the intended `user.name` / `user.email` in the target repository.
GitHub operations need authenticated `gh` with access to the selected repo. Local
static checks and `-h` do not require GitHub or a configured identity. Local-device
`--live` / `--su` operations require a compatible Android environment and permissions;
they do not target a phone connected to a workstation automatically.

## Validate changes

```sh
python3 -m unittest discover -s tests -v
bash bundle.sh
git diff --check
```

The offline regression suite exercises real temporary Git repositories, malformed
inputs, mock GitHub responses, isolated installation destinations and bundle/license
contents. CI also checks that committed bundles match their sources. These checks
validate the helpers and packaging, not Android builds or model behavior.

## Credit policy (applies to ALL skills)

- Forked third-party skills keep **full original credit** — `CREDITS.md` in their folder,
  an entry here, and unchanged text (see the REA fork).
- Borrowed methods cite their source (URL + SHA) when non-trivial.
- Commit examples use placeholders; personal repo maps and sync logs stay
  in gitignored `_personal/` (same column layout as
  [`rom-device-dev`'s template](skills/rom-device-dev/references/upstreams-template.md)).
- No AI attribution trailers anywhere — human co-authors only.

## Layout

```
skills/<name>/SKILL.md         instructions (Agent Skills format)
skills/<name>/references/*.md  detail, loaded on demand
skills/<name>/scripts/*        tools the skill runs
skills/<name>/CREDITS.md       required for forked skills
dist/<name>.md                 single-file bundles (./bundle.sh)
_personal/                     gitignored private device data (yours; never pushed)
AGENTS.md                      index for agents that open this repo
```
