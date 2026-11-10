#!/usr/bin/env bash
# Link every skill in skills/ into the folders coding agents load skills from.
#
#   ./install.sh            link into ~/.agents/skills, ~/.claude/skills and every
#                           other agent folder whose agent is installed
#   ./install.sh --to DIR   link only into DIR (repeatable)
#   ./install.sh --force    back up a conflicting file, directory or symlink
#   ./install.sh --list     show where each skill is linked
#   ./install.sh --remove   remove links that point into this repo
#
# Links, not copies: `git pull` here updates every agent at once.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
MODE=install FORCE=0 EXTRA=()
while [ $# -gt 0 ]; do
    case "$1" in
        --to) [ $# -ge 2 ] && [ -n "$2" ] && [[ "$2" != -* ]] || { echo "--to needs a directory" >&2; exit 1; }; EXTRA+=("$2"); shift ;;
        --force) FORCE=1 ;;
        --list) MODE=list ;;
        --remove) MODE=remove ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option $1" >&2; exit 1 ;;
    esac
    shift
done

targets=("$HOME/.agents/skills" "$HOME/.claude/skills")    # shared location, Claude Code
[ -d "$HOME/.codex" ] && targets+=("$HOME/.codex/skills")           # OpenAI Codex CLI
[ -d "$HOME/.gemini" ] && targets+=("$HOME/.gemini/skills")         # Gemini CLI
[ -d "$HOME/.gemini/config" ] && targets+=("$HOME/.gemini/config/skills")   # Antigravity CLI
if [ ${#EXTRA[@]} -gt 0 ]; then targets=("${EXTRA[@]}"); fi

for skill in "$ROOT"/skills/*/; do
    skill=${skill%/}
    [ -f "$skill/SKILL.md" ] || continue
    name=$(basename "$skill")
    for t in "${targets[@]}"; do
        dest="$t/$name"
        case "$MODE" in
        list)
            if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$skill" ]; then echo "linked   $dest"
            elif [ -e "$dest" ] || [ -L "$dest" ]; then echo "OTHER    $dest"
            else echo "missing  $dest"; fi ;;
        remove)
            if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$skill" ]; then rm "$dest"; echo "removed  $dest"; fi ;;
        install)
            mkdir -p "$t"
            if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$skill" ]; then
                echo "linked   $dest"; continue
            elif [ -e "$dest" ] || [ -L "$dest" ]; then
                if [ "$FORCE" = 1 ]; then
                    backup=$(mktemp -d "$t/$name.bak.XXXXXX")
                    mv "$dest" "$backup/$name"
                    ln -s "$skill" "$dest"
                    echo "backup   $backup/$name"
                else
                    echo "skip     $dest (another installation is there; --force backs it up)"; continue
                fi
            else
                ln -s "$skill" "$dest"
            fi
            echo "linked   $dest" ;;
        esac
    done
done
