# agent-skills

Reusable Android skills for AI coding agents. One copy in this repo, linked into every
agent. Skills are written generically so they work on any device or ROM; personal
repo-specific notes belong in `_personal/` (gitignored, never published).

| Skill | What it covers | Credit |
|---|---|---|
| [`read-android-source`](skills/read-android-source/SKILL.md) | Reading upstream Android source online: AOSP, Qualcomm CodeLinaro (LA. tags), LineageOS, custom-ROM mirrors; the AOSP/CLO/Lineage tree map | original work, this repo's author |
| [`reverse-engineering-cherry-picking`](skills/reverse-engineering-cherry-picking/SKILL.md) | Android RE (blobs, HALs, APKs, firmware, live device, SELinux), cherry-picking/porting with credit, upstream sync, build-safety without builds, history surgery, parallel-tree sync | original work, this repo's author (including battle-tested case studies) |
| [`rom-device-dev`](skills/rom-device-dev/SKILL.md) | Android ROM device-tree bring-up and maintenance for any device/ROM: runbook rules, manifests, subsystem fixes, first-boot debugging, kernel-level work, integrity hygiene | original work, this repo's author |
| [`reverse-engineer-anything`](skills/reverse-engineer-anything/SKILL.md) | **Verbatim fork of [REA](https://github.com/morluto/rea)** (npm `rea-agents`) — native, managed, Electron/JS, packaged, firmware and browser RE with agents | **FULL credit to [REA](https://github.com/morluto/rea) and its authors** — see [`CREDITS.md`](skills/reverse-engineer-anything/CREDITS.md); synced to upstream `dba8a31` |
| [`ponytail`](skills/ponytail/SKILL.md) | **Verbatim copy of the core skill of [Ponytail](https://github.com/DietrichGebert/ponytail)** (MIT): the smallest change that fully solves the task | **FULL credit to [Ponytail](https://github.com/DietrichGebert/ponytail) and its author** — see [`CREDITS.md`](skills/ponytail/CREDITS.md) |

## Install

```sh
git clone https://github.com/fuzailmansuri/agent-skills ~/agent-skills
bash ~/agent-skills/install.sh          # links skills into every agent found
bash ~/agent-skills/install.sh --list   # where each skill is linked
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

Update everywhere: `git -C ~/agent-skills pull`.

## Requirements for the scripts

`git`, `python3` (3.8+, stdlib only), `gh` logged in (`gh auth status`), and your own
`git config user.name` / `user.email` set in the target repo (the scripts no longer carry a
default identity). On-phone work needs `su`.

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
