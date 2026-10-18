---
name: rom-device-dev
description: >-
  Engineering runbook and strict rules for developing and maintaining an Android ROM device
  tree for any device and ROM (device/, hardware/, proprietary vendor, kernel, manifests,
  sepolicy). Use when doing device bring-up or ongoing maintenance, porting subsystem
  behaviour between trees, first-boot debugging of a broken feature, Android kernel-level
  work (bring-up, modules, devicetrees), framework-level props and integrity plumbing,
  SystemUI/Launcher daily-driver customization, or audits where no build is available.
---

# ROM device development runbook

Ground rules every task inherits. Detail lives in `references/`; upstream mechanics and
credit live in the `reverse-engineering-cherry-picking` skill.

## Ground rules

1. **Identity.** Commits carry the **user's own configured git identity** (`git config
   user.name` / `user.email`). Verify before every commit session; never commit with a work,
   default or unrelated identity. Authorship of other people's code rules:
   `reverse-engineering-cherry-picking`, `references/credit.md`.
2. **Commit style.** Technical only: what changed, why, the mechanism. No "inspired by"
   references to other OSes, no milestones, no AI attribution trailers. Human co-authors are
   always credited.
3. **No builds.** Nothing gets built to test — work must be right by inspection, symbol
   checking and `scripts/preflight.py` (from the cherry-picking skill). Propose change sets
   whose dependencies are proven to exist in the active tree; never propose whole-ROM ports
   that need trial build cycles.
4. **No big fetches.** Never clone large histories on device storage/budget. Fetch single
   commits or patches via the API (`fetch-patch.py`, `vendor-api-commit.py`).
5. **PR safety.** Never open PRs, issues or comments against upstream repositories. Any
   push/PR targets repositories the **user controls** only. Verify the remote URL before
   pushing.
6. **Private device data.** Actual fork maps, sync logs and open leads live in `_personal/`
   (gitignored). The public, reusable template lives in
   [references/upstreams-template.md](./references/upstreams-template.md). Update the private
   log after every sync; never commit real names/SHAs into the shared template.
7. **History protection.** Never rewrite a pushed branch without an explicit fresh
   instruction; take backups first. Full safe-surgery method:
   `reverse-engineering-cherry-picking`, `references/history-surgery.md`.

## Reference index

| Task | Read |
|---|---|
| Device tree / HAL audit, sibling-device reasoning | `references/device-tree-audit.md` |
| A feature broke after first boot — systematic debug | `references/first-boot-debugging.md` |
| Git identity, commit style, credit summary | `references/git-conventions.md` |
| Repo layout, manifests, fast patching | `references/repo-manifests.md` |
| Kernel-level work: bring-up, modules, devicetrees | `references/kernel-level-work.md` |
| Props spoofing & integrity hygiene | `references/props-integrity.md` |
| SystemUI / Launcher customization | `references/ui-ux-systemui.md` |
| Where to keep the fork map and sync log | `references/upstreams-template.md` |
