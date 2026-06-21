#!/bin/bash
set -e

success() { echo -e "\033[32;1m.. $@\033[0m"; }
step() { echo -e "\033[34;1m== $@\033[0m"; }
run() { echo -e "\033[35;1m \$ $@\033[0m"; "$@"; }

DUMP_FILE="clam.svn"
REPO_PREFIX="clam-git"

# Files to track for versioning (exclude dump - slow and won't change)
CHECKSUM_FILES=(
    "import.sh"
    "repomigrate/cli.py"
    "import.lift"
    "emptycommits.tsv"
)

next_repo() {
    local prefix=$1
    shift
    local files=("$@")
    
    local checksum=$(cat "${files[@]}" 2>/dev/null | md5sum | cut -c1-8)
    
    # Find last repo by sequence number
    local last=$(ls -d ${prefix}-*-*/ 2>/dev/null | sort -t'-' -k2 -n | tail -1)
    
    # If last repo exists and has same checksum, reuse it
    if [ -n "$last" ] && [[ "$last" =~ ${prefix}-[0-9]+-${checksum}/ ]]; then
        rm -rf "${last%/}"
        echo "${last%/}"
        return
    fi
    
    # Otherwise, create new with next sequence
    local seq=0
    [ -n "$last" ] && [[ "$last" =~ ^${prefix}-([0-9]+)- ]] && seq=$(( 10#${BASH_REMATCH[1]} + 1 ))
    
    printf "%s-%04d-%s\n" "$prefix" "$seq" "$checksum"
}

REPO_DIR=$(next_repo "$REPO_PREFIX" "${CHECKSUM_FILES[@]}")

step Generate emptycommits.lift from emptycommits.tsv
mkdir -p generated
tail -n +2 emptycommits.tsv | while IFS=$'\t' read tagged removed; do
    echo "<${tagged}> append \"\\nSVN-Revision: ${removed}\""
    echo "tag delete /emptycommit-${removed}/"
done > generated/emptycommits.lift

step Import from $DUMP_FILE
run reposurgeon "read <$DUMP_FILE" "script import.lift" "rebuild $REPO_DIR"

# Fix GraphicsViewNetworkCanvas branch (see notes.md)
run git -C "$REPO_DIR" filter-repo --force --path-rename :NetworkEditor/ --refs GraphicsViewNetworkCanvas

success "Done: $REPO_DIR"

(cd $REPO_DIR; tig --all)


