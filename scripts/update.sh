#!/bin/bash
# Lucid self-update: pull the latest version of this skill from its source repo.
#
# Usage:
#   ./update.sh              # fast-forward pull; refuses if the worktree is dirty
#   ./update.sh --dry-run    # show what would happen, change nothing
#   ./update.sh --force      # discard local edits and hard-reset to origin (DESTRUCTIVE)
#   ./update.sh --help       # print this usage
#
# Journals and data live outside the repo (~/.hermes/commons/{journals,data}/ocas-lucid)
# and are never touched here.
#
# Exit codes:
#   0  updated / already up to date
#   2  bad usage
#   3  worktree has uncommitted changes (refused; use --force to override)
#   4  local commits diverged from origin (refused; needs manual reconciliation)
set -uo pipefail

usage() {
  # Print the comment header only: lines between the shebang and the first
  # non-comment line. Robust to edits above the usage block.
  sed -n '2,${/^#/!q;s/^# \{0,1\}//p;}' "$0"
  exit "${1:-0}"
}

DRY_RUN=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --help|-h)   usage 0 ;;
    --dry-run)   DRY_RUN=1 ;;
    --force)     FORCE=1 ;;
    *) echo "error: unknown argument '$arg' (try --help)" >&2; usage 2 ;;
  esac
done

cd "$(dirname "$0")/.." || { echo "error: cannot enter skill directory" >&2; exit 3; }

# Refuse to clobber uncommitted work unless explicitly forced. A silent
# `git reset --hard` here used to destroy local edits with no warning and no
# way to recover them.
if [[ $FORCE -eq 0 ]]; then
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo "error: worktree has uncommitted changes; refusing to reset." >&2
    echo "       Review with 'git status' / 'git diff', commit them, or re-run with --force" >&2
    echo "       to discard local edits and hard-reset to origin." >&2
    exit 3
  fi
fi

# Refuse when local commits would be orphaned by the pull.
if [[ $FORCE -eq 0 ]]; then
  if ! git diff --quiet HEAD @{u} 2>/dev/null; then
    echo "error: local commits have diverged from origin; refusing to pull." >&2
    echo "       Reconcile manually (rebase/merge), or re-run with --force to discard them." >&2
    exit 4
  fi
fi

run_git() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] git $*"
  else
    git "$@"
  fi
}

if [[ $FORCE -eq 1 ]]; then
  run_git reset --hard HEAD
  run_git clean -fd
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "[dry-run] git pull --ff-only"
  exit 0
fi

if ! git pull --ff-only; then
  echo "error: git pull --ff-only failed (remote moved or network unavailable)." >&2
  exit 4
fi

echo "lucid updated: $(git rev-parse --short HEAD)"
