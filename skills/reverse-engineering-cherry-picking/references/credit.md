# Credit and provenance

Every commit built from someone else's work credits them. Human co-authors are required;
only AI attribution is banned. The porter's identity = the user's `git config` ("you"
below).

| Kind of commit | Author | Message |
|---|---|---|
| Straight pick (`git cherry-pick -x`, `git am`, `fetch-patch.py --am`) | upstream author (kept automatically) | upstream message; `-x` adds the source SHA |
| Adapted or squashed port of their commit(s) | upstream author of the main commit | their subject when the change is the same; body cites `https://.../commit/FULLSHA`; `Co-authored-by:` for other upstream authors and for the porter; `Signed-off-by: <porting author>` |
| Our own follow-up that mirrors their change (vendor blob drop matching their device-tree commit) | you | cite their commit; `Co-authored-by: <them>`; `Signed-off-by: <you>` |
| Our own work | you | `Signed-off-by: <you>` |

The committer is always the user's identity. `python3 scripts/credit.py O/R SHA...` prints
the author, the footer and the command. `vendor-api-commit.py` takes `--author` and
`--co-author` for vendor commits.

Keep the upstream subject on ports. `upstream-diff.sh` matches by subject, so the next sync
shows them as HAVE instead of re-proposing them.

## Example (anonymized; lights HAL port)

```
device: Switch to OSS lights HAL              Author: Upstream Maintainer <them@example.dev>

Drive the LED controller through android.hardware.light-service.<vendor> ...

Based on
https://github.com/<upstream>/<their-device-tree>/commit/1f2f5933...full-sha...
https://github.com/<upstream>/<their-hardware-tree>/commit/049ecdf0...full-sha...

Co-authored-by: Upstream Maintainer <them@example.dev>
Signed-off-by: You <you@example.org>
```

```
device: Drop QTI lights service               Author: You <you@example.org>

The LEDs are driven by android.hardware.light-service.<vendor> now.
Matches the proprietary-files.txt change in
https://github.com/<upstream>/<their-device-tree>/commit/1f2f5933...full-sha...

Co-authored-by: Upstream Maintainer <them@example.dev>
Signed-off-by: You <you@example.org>
```

Forgot credit on something already pushed? Amend the tip and push
`--force-with-lease=BR:OLDSHA`, keeping the tree identical. For a vendor repo, create a new
commit object with the same tree and parent through the API.

## History surgery for credit (when a rewrite is justified)

Full playbook: `references/history-surgery.md`. Summary: backups and a recorded tree SHA
first; identity normalization and trailer additions are message-only (final tree must stay
byte-identical); consolidation of loose commits is done by squash, only on adjacent commits;
net-zero pairs are deleted after patch-level verification; force-pushing is an explicit
fresh instruction.
