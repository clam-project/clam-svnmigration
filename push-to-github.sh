#!/bin/bash
set -e

run() { echo -e "\033[35;1m\$ $@\033[0m"; "$@"; }
fail() { echo -e "\033[31;1m!! $@\033[0m"; exit -1; }

REPO_DIR=$(ls -d clam-git-* 2>/dev/null | sort | tail -1)
[ -z "$REPO_DIR" ] && { fail "No clam-git-* directory found"; }

# REMOTE_URL="git@github.com:clam-project/clam.git"
REMOTE_URL="git@github.com:vokimon/clam-import-test.git"

PUSH_OPTS=(--force --dry-run)
[ "${1:-}" = "--push" ] && PUSH_OPTS=(--force)

run git -C "$REPO_DIR" remote add origin "$REMOTE_URL"
run git -C "$REPO_DIR" push origin main:main "${PUSH_OPTS[@]}"
run git -C "$REPO_DIR" push origin --all "${PUSH_OPTS[@]}"
run git -C "$REPO_DIR" push origin --tags "${PUSH_OPTS[@]}"

run git -C "$REPO_DIR" fetch origin

for rb in $(git -C "$REPO_DIR" branch -r --list 'origin/*' --format='%(refname:short)' | sed 's|origin/||'); do
    echo "rb: $rb"
    git -C "$REPO_DIR" rev-parse --verify "$rb" >/dev/null 2>&1 || \
        run git -C "$REPO_DIR" push origin --delete "$rb" "${PUSH_OPTS[@]}"
done

for rt in $(git -C "$REPO_DIR" ls-remote --tags origin --format='%(refname:short)' 2>/dev/null); do
    echo "rt: $rt"
    git -C "$REPO_DIR" tag -l "$rt" >/dev/null 2>&1 || \
        run git -C "$REPO_DIR" push origin --delete "$rt" "${PUSH_OPTS[@]}"
done

run git -C "$REPO_DIR" remote remove origin
