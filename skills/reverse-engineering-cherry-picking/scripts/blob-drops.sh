#!/usr/bin/env bash
# Net blob changes in a proprietary list between two revisions. Line diffs of
# proprietary-files.txt exaggerate (sections get reordered on every regen);
# this compares the sets of files instead.
#
# usage: blob-drops.sh -C <clone> [-l <list>] <old-rev> <new-rev> [<fork-rev>]
#
#   -l  list file (default proprietary-files.txt)
#   With <fork-rev>, every dropped/added entry is marked with whether the fork
#   still ships it.
set -euo pipefail
unset -f grep sort sed comm 2>/dev/null || true

C= L=proprietary-files.txt
while getopts "C:l:h" o; do
    case "$o" in C) C=$OPTARG ;; l) L=$OPTARG ;; *) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;; esac
done
shift $((OPTIND - 1))
[ -n "$C" ] && [ $# -ge 2 ] || { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
OLD=$1 NEW=$2 FORK=${3:-}

TMP=$(mktemp -d "${TMPDIR:-${PREFIX:-}/tmp}/blobs.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# Strip comments, the leading "-" (module marker), ";FLAGS" and "|sha1" suffixes.
norm() {
    git -C "$C" show "$1:$L" \
        | sed -e 's/#.*$//' -e 's/^[[:space:]]*-//' -e 's/[;|].*$//' -e 's/[[:space:]]*$//' \
        | grep -v '^$' | LC_ALL=C sort -u
}
norm "$OLD" > "$TMP/old"
norm "$NEW" > "$TMP/new"
[ -n "$FORK" ] && norm "$FORK" > "$TMP/fork"

mark() {
    while read -r f; do
        if [ -z "$FORK" ]; then echo "  $f"
        elif grep -qxF -- "$f" "$TMP/fork"; then echo "  [fork has  ] $f"
        else echo "  [fork lacks] $f"; fi
    done
}

dropped=$(LC_ALL=C comm -23 "$TMP/old" "$TMP/new")
added=$(LC_ALL=C comm -13 "$TMP/old" "$TMP/new")
echo "$L: $OLD -> $NEW"
echo "dropped $(printf '%s' "$dropped" | grep -c . || true), added $(printf '%s' "$added" | grep -c . || true)"
echo
echo "== dropped"
[ -n "$dropped" ] && printf '%s\n' "$dropped" | mark
echo
echo "== added"
[ -n "$added" ] && printf '%s\n' "$added" | mark
exit 0
