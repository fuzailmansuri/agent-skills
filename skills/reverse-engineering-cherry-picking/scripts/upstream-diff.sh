#!/usr/bin/env bash
# Classify an upstream branch's commits against a fork branch, without touching
# any of the clone's branches (all trial picks happen in a throwaway worktree).
#
# usage: upstream-diff.sh -C <clone> -u <remote|url> -b <upstream-branch> -f <fork-ref>
#                         [-s <since-commit>] [-p <self-path>] [-k <keep-branch>]
#
#   -C  local clone of the fork (small repos only: device trees, hardware/*, packages)
#   -u  upstream remote name or URL (fetched into refs/remotes/usync/<branch>)
#   -b  upstream branch
#   -f  fork ref, e.g. origin/seventeen (re-fetched when it names a remote branch)
#   -s  only list upstream commits after this one (checkpoint from sync-log.md);
#       default: the merge base
#   -p  this repo's own path in the source tree (e.g. device/<vendor>/<codename>),
#       hidden from the "refs" column
#   -k  keep the CLEAN picks on a new local branch with this name
#
# Status per upstream commit (oldest first):
#   HAVE      same patch-id or same subject already on the fork, or picks to a no-op
#   CLEAN     cherry-picks cleanly (picks are cumulative, in upstream order)
#   CONFLICT  does not apply; conflicting files listed
#
# "refs" lists hardware/, vendor/, device/ and kernel/ paths named in the
# commit's added lines (outside proprietary lists and .prop files). A path
# the fork's manifest does not carry means the commit depends on another repo.
set -euo pipefail
unset -f grep sort sed awk tr cut 2>/dev/null || true

usage() { sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-1}"; }

C= U= B= F= S= P= K=
while getopts "C:u:b:f:s:p:k:h" o; do
    case "$o" in
        C) C=$OPTARG ;; u) U=$OPTARG ;; b) B=$OPTARG ;; f) F=$OPTARG ;;
        s) S=$OPTARG ;; p) P=$OPTARG ;; k) K=$OPTARG ;; h) usage 0 ;; *) usage ;;
    esac
done
[ -n "$C" ] && [ -n "$U" ] && [ -n "$B" ] && [ -n "$F" ] || usage

g() { git -C "$C" "$@"; }
NAME=${SYNC_NAME:-$(git config user.name)}
EMAIL=${SYNC_EMAIL:-$(git config user.email)}

g fetch -q --no-tags "$U" "+refs/heads/$B:refs/remotes/usync/$B"
UP=refs/remotes/usync/$B

r=${F%%/*} br=${F#*/}
if [ "$r" != "$F" ] && g remote | grep -qx "$r"; then
    g fetch -q --no-tags "$r" "+refs/heads/$br:refs/remotes/$r/$br"
fi

MB=$(g merge-base "$F" "$UP") || { echo "no common history between $F and $U $B" >&2; exit 1; }
BASE=$MB
if [ -n "$S" ]; then
    if g merge-base --is-ancestor "$S" "$UP" 2>/dev/null; then
        BASE=$(g rev-parse "$S^{commit}")
    else
        echo "warning: $S is not in $B's history (rewritten upstream?), using the merge base" >&2
    fi
fi

mapfile -t COMMITS < <(g rev-list --reverse --no-merges "$BASE..$UP")
MERGES=$(g rev-list --count --merges "$BASE..$UP")
UPTIP=$(g rev-parse "$UP")

echo "upstream  $U $B @ ${UPTIP:0:12}"
echo "fork      $F @ $(g rev-parse --short=12 "$F")"
echo "base      ${BASE:0:12}$([ "$BASE" = "$MB" ] && echo " (merge base)" || echo " (checkpoint)")"
echo "commits   ${#COMMITS[@]} (merges skipped: $MERGES)"
[ "${#COMMITS[@]}" -gt 0 ] || { echo "nothing new upstream"; exit 0; }

TMP=$(mktemp -d "${TMPDIR:-${PREFIX:-}/tmp}/usync.XXXXXX")
WT=$TMP/wt
cleanup() {
    g worktree remove --force "$WT" >/dev/null 2>&1 || true
    g worktree prune >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap cleanup EXIT
g worktree add -q --detach "$WT" "$F"
w() { git -C "$WT" -c user.name="$NAME" -c user.email="$EMAIL" "$@"; }

declare -A SAME=()
while read -r mark sha; do
    [ "$mark" = "-" ] && SAME[$sha]=1
done < <(g cherry "$F" "$UP" "$MB")

g log --format=%s "$MB..$F" > "$TMP/subjects"

CLEAN=() n_have=0 n_clean=0 n_conf=0
printf '\n%-8s  %-8s  %-10s  %-11s  %s\n' STATUS COMMIT DATE SIZE SUBJECT
for c in "${COMMITS[@]}"; do
    subj=$(g log -1 --format=%s "$c")
    day=$(g log -1 --format=%ad --date=short "$c")
    short=$(g rev-parse --short=8 "$c")
    size=$(g show --numstat --format= "$c" | awk '{a+=$1; d+=$2} END {printf "+%d/-%d", a, d}')
    refs=$( { g show --format= "$c" -- . ':(exclude)proprietary-*.txt' ':(exclude)*.prop' \
        | grep '^+' \
        | grep -oE '(^|[^/A-Za-z0-9_.$-])(hardware|vendor|device|kernel)/[A-Za-z0-9_.+-]+(/[A-Za-z0-9_.+-]+)?' \
        | sed -E -e 's#^[^hvdk]##' -e 's#[.]+$##' \
        | grep -vE '^vendor/(bin|xbin|lib|lib64|etc|firmware|app|priv-app|framework|overlay|usr|gpu|dsp|rfs|radio|media|camera|odm)(/|$)' \
        | { if [ -n "$P" ]; then grep -v "^${P%/}"; else cat; fi; } \
        | sort -u | tr '\n' ' '; } || true)
    if [ -n "${SAME[$c]:-}" ]; then
        st=HAVE note="same patch"; n_have=$((n_have + 1))
    elif grep -qxF -- "$subj" "$TMP/subjects"; then
        st=HAVE note="same subject"; n_have=$((n_have + 1))
    elif w cherry-pick --allow-empty --keep-redundant-commits "$c" >/dev/null 2>&1; then
        if git -C "$WT" diff --quiet HEAD~1 HEAD; then
            git -C "$WT" reset -q --hard HEAD~1
            st=HAVE note="no-op on fork"; n_have=$((n_have + 1))
        else
            st=CLEAN note=""; CLEAN+=("$short"); n_clean=$((n_clean + 1))
        fi
    else
        files=$(git -C "$WT" diff --name-only --diff-filter=U | tr '\n' ' ')
        git -C "$WT" cherry-pick --abort >/dev/null 2>&1 || git -C "$WT" reset -q --hard
        st=CONFLICT note="conflicts: ${files:-<none, pick failed>}"; n_conf=$((n_conf + 1))
    fi
    printf '%-8s  %-8s  %-10s  %-11s  %s\n' "$st" "$short" "$day" "$size" "$subj"
    [ -n "$note" ] && printf '%42s%s\n' "" "$note"
    [ -n "$refs" ] && printf '%42srefs: %s\n' "" "$refs"
done

echo
echo "HAVE $n_have  CLEAN $n_clean  CONFLICT $n_conf"
[ "${#CLEAN[@]}" -gt 0 ] && echo "clean picks, in order: ${CLEAN[*]}"
if [ -n "$K" ] && [ "${#CLEAN[@]}" -gt 0 ]; then
    g branch "$K" "$(git -C "$WT" rev-parse HEAD)"
    echo "kept the clean picks on local branch $K"
fi
echo "checkpoint for sync-log.md: $UPTIP"
