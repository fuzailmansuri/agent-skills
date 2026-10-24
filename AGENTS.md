# Agent skills

Each folder in `skills/` is a skill in the Agent Skills format: a `SKILL.md` with YAML
`name` + `description`, instructions below it, and optional `references/`, `scripts/`, and
(for forked skills) `CREDITS.md`.

**Using a skill:** when a task matches a skill's description, read its `SKILL.md` first and
follow it. Open files in `references/` only when `SKILL.md` points there. Run scripts from
the skill's folder (`python3 scripts/X.py -h`).

| Skill | Use when |
|---|---|
| `read-android-source` | Read upstream Android source online without cloning: AOSP, Qualcomm CLO (LA. tags), LineageOS, other ROM mirrors; locating implementations, matching tags, cross-checking device trees |
| `reverse-engineering-cherry-picking` | Reverse engineering Android blobs/HALs/apps/firmware/live device, SELinux denials, picking or porting commits from any ROM/kernel/maintainer, syncing upstream pushes, build-safety without builds, safe git history surgery, parallel-tree sync |
| `rom-device-dev` | Device-tree bring-up or maintenance on any Android ROM: runbook rules, subsystem fixes (display, vibration, audio, camera, fingerprint), first-boot debugging, manifests and fast patching, kernel-level work (bring-up, modules, devicetrees), props spoofing & integrity hygiene |
| `reverse-engineer-anything` | General artifact reverse engineering via the REA toolchain (MCP server, decompilers) — **forked; all credit to [REA](https://github.com/morluto/rea)**, see its `CREDITS.md` |
| `ponytail` | Coding discipline: the smallest complete change, no unrequested code — **vendored; all credit to [Ponytail](https://github.com/DietrichGebert/ponytail)**, see its `CREDITS.md` |

**Editing this repo:**
- Keep each `SKILL.md` short; detail goes in `references/`.
- Scripts are Python 3 stdlib or bash only, and every one has `-h`.
- Committing identity = your own git config; technical messages, no AI trailers.
- Run `bash bundle.sh` after edits so `dist/` stays current.
- Private device data (fork maps, sync logs) lives in `_personal/` — gitignored, never
  committed; the public templates live in the device skill's `references/`.
