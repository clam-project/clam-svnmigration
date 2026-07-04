#!/bin/bash
set -e

success() { echo -e "\033[32;1m.. $@\033[0m"; }
step() { echo -e "\033[34;1m== $@\033[0m"; }
run() { echo -e "\033[35;1m\$ $@\033[0m"; "$@"; }
norun() { echo -e "\033[35mSkipped $ $@\033[0m";}
warn() { echo -e "\033[33;1m!! $@\033[0m"; }

find_commit_by_svn_rev() {
    local rev=$1
    local repo=${2:-.}
    git -C "$repo" log --all --grep="SVN-Revision: ${rev}$" --format="%H" | head -1
}

is_merge_commit() {
    local repo=${2:-.}
    [ "$(git -C "$repo" cat-file -p $1 | grep -c '^parent ')" -ge 2 ]
}

is_branch() {
    local repo=${2:-.}
    git -C "$repo" rev-parse --verify "$1" >/dev/null 2>&1
}

make_merge_commit() {
    local branch=$1
    local svn_rev=$2
    local repo=${3:-.}

    local commit=$(find_commit_by_svn_rev "$svn_rev" "$repo")
    [ -z "$commit" ] && { echo "No commit found with SVN-Revision: ${svn_rev}"; return 1; }
    is_branch "$branch" "$repo" || { echo "Branch does not exist: $branch"; return 1; }
    is_merge_commit "$commit" "$repo" && { echo "Already a merge commit: ${commit}"; return 0; }

    local msg=$(git -C "$repo" log -1 --format='%B' ${commit})

    echo "Rewriting ${commit} (SVN-Revision: ${svn_rev}) as merge of ${branch}"

    git -C "$repo" filter-branch --force --commit-filter "
        if [ \"\$GIT_COMMIT\" = \"${commit}\" ]; then
            git commit-tree $(git -C "$repo" rev-parse ${commit}^{tree}) \
                -p $(git -C "$repo" rev-parse ${commit}^) \
                -p $(git -C "$repo" rev-parse ${branch}) \
                -m \"${msg}\"
        else
            git commit-tree \"\$@\"
        fi
    " HEAD
    step Clean up filter-branch backups
    git -C "$REPO_DIR" for-each-ref refs/original/ --format='%(refname)' | xargs -I{} git -C "$REPO_DIR" update-ref -d {}
}

tag_from_tsv() {
    local repo=$1
    local tsv=$2
    [ -f "$tsv" ] || { warn "File not found: $tsv"; return 1; }

    tail -n +2 "$tsv" | while IFS=$'\t' read -r rev tag_name; do
        [ "$rev" -eq 0 ] 2>/dev/null && continue
        [ -z "$tag_name" ] && continue

        local commit=$(find_commit_by_svn_rev "$rev" "$repo")
        if [ -z "$commit" ]; then
            warn "No commit found for SVN-Revision $rev (tag: $tag_name), skipping"
            continue
        fi

        run git -C "$repo" tag -f "$tag_name" "$commit"
    done
}

rename_tags() {
    local repo=$1
    local tsv=$2
    [ -f "$tsv" ] || { warn "File not found: $tsv"; return 1; }

    grep -v '^#' "$tsv" | while IFS=$'\t' read -r old_tag new_tags; do
        [ -z "$old_tag" ] && continue
        for new_tag in $new_tags; do
            [ -z "$new_tag" ] && continue
            run git -C "$repo" tag "$new_tag" "$old_tag"
        done
        #run git -C "$repo" tag -d "$old_tag"
    done
}

ORIGINAL_DUMP_FILE="clam-original.svn"
DUMP_FILE="clam-cleaned.svn"
REPO_PREFIX="clam-git"

# Files to track for versioning (exclude dump - slow and won't change)
CHECKSUM_FILES=(
    "$DUMP_FILE"
    "import.sh"
    "repomigrate/cli.py"
    "import.lift"
    "emptycommits.tsv"
    "tag-rename.tsv"
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

generate_empty_commits_lift() {
    mkdir -p generated
    tail -n +2 emptycommits.tsv | while IFS=$'\t' read tagged removed; do
        echo "<${tagged}> append \"\\nSVN-Revision: ${removed}\""
        #echo "tag delete /emptycommit-${removed}/"
    done > generated/emptycommits.lift
}

REPO_DIR=$(next_repo "$REPO_PREFIX" "${CHECKSUM_FILES[@]}")

run repomigrate preprocess "${ORIGINAL_DUMP_FILE}" "${DUMP_FILE}"

step Generate emptycommits.lift from emptycommits.tsv
run generate_empty_commits_lift

step Import from $DUMP_FILE
run reposurgeon "read --preserve <$DUMP_FILE" "script import.lift" "rebuild $REPO_DIR"

# This is done now by fixCamvasBranch directly on the svndump before this script
#step Fix GraphicsViewNetworkCanvas branch
#MERGE_BASE=$(git -C "$REPO_DIR" merge-base GraphicsViewNetworkCanvas HEAD)
#run git -C "$REPO_DIR" filter-repo --force --path-rename :NetworkEditor/ --refs ${MERGE_BASE}..GraphicsViewNetworkCanvas

#step Merge GraphicsViewNetworkCanvas to trunk
#run make_merge_commit  GraphicsViewNetworkCanvas 13429 $REPO_DIR

#step Tag releases from tarballs
run tag_from_tsv "$REPO_DIR" tarball-revisions.tsv

step Rename tags from tag-rename.tsv
run rename_tags "$REPO_DIR" tag-rename.tsv

success "Done: $REPO_DIR"

(cd $REPO_DIR; tig --all)


