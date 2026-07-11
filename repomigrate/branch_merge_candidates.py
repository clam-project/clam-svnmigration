
import sys
from pathlib import Path
from collections import OrderedDict
from consolemsg import step, warn, success
import typer
from .svndump import parse_svndump, dump_svndump, SvnNode
from os.path import commonprefix
from dataclasses import dataclass


def node_path_branch(path):
    if path.startswith(b'trunk'): return b'trunk'
    if path.startswith(b'branches/unlabeled'):
        return None
    if path.startswith(b'branches'):
        return b'/'.join(path.split(b'/')[:2])
    if path.startswith(b'tags'):
        return b'/'.join(path.split(b'/')[:2])
    warn(f"Unexpedted prefix {path.decode()}")
    return None

def branch_merge_candidates(
    input_dump_file: Path = typer.Argument(..., help="Path to the input SVN dump file"),
    output_dump_file: Path = typer.Argument(..., help="Path to the output SVN dump file"),
):
    """Analyzes svn branches to estimated merge points of branches."""

    step(f"Reading {input_dump_file}")
    data = input_dump_file.read_bytes()
    dump = parse_svndump(data)

    step("Split revisions by branches")
    branches = dict()
    for rev_number, rev in enumerate(dump.revisions):
        log = (rev.properties.get(b'svn:log') or b"<empty log>").decode()
        if not rev.nodes:
            if 'was initially added on branch' in log:
                # Know case of cvs2svn empty commit
                continue
            warn(f"Revision {rev_number} has no nodes\n{log}")
            continue
        edited_branches = {
            branch for branch in (
                node_path_branch(node.fields[b'Node-path'])
                for node in rev.nodes
            )
            if branch is not None
        }
        if not edited_branches:
            continue
        if edited_branches == {b'trunk', b'branches', b'tags'}:
            # Initial commit creating the structure
            edited_branches = {b'trunk'}

        if len(edited_branches) != 1:
            warn(f"Expected single branch revision {rev_number} but found: {b', '.join(edited_branches).decode()}\n{log}")
        for branch in edited_branches:
            branches.setdefault(branch, []).append(rev_number)

    if False:
        for name, revisions in branches.items():
            print(name, revisions)

    step("Computing modified files in each branch")

    def modified_rev_files(rev_number, branch):
        rev = dump.revisions[rev_number]
        log = (rev.properties.get(b'svn:log') or b'<empty log>').decode()
        if 'manufactured' in log: return set()
        return {
            path[len(branch) + 1:]
            for path in [
                node.fields[b'Node-path']
                for node in rev.nodes
            ]
            if path.startswith(branch)
            and path != branch
        }

    ignored_branches = [
        b'branches/development-branch',
        b'branches/INITIAL_IMPORT_VENDOR_TAG',
    ]
    modified_files_per_branch = dict()
    for branch, revisions in branches.items():
        if branch == b'trunk': continue
        if branch.startswith(b'tags'): continue
        if branch in ignored_branches: continue

        modified = set()
        for rev_number in revisions:
            modified |= modified_rev_files(rev_number, branch)

        if not modified:
            warn(f"Empty branch: {branch.decode()}")
            continue

        # Special case: This branch has no top level dir
        if branch == b'branches/GraphicsViewNetworkCanvas':
            modified = { b'NetworkEditor/' + file for file in modified }

        modified_files_per_branch[branch] = modified

    if False:
        for name, files in modified_files_per_branch.items():
            print(name)
            for file in sorted(files):
                print(f'\t{file.decode()}')

    development_branch_revisions = branches[b'branches/development-branch']
    step(f"development-branch {development_branch_revisions[0]}-{development_branch_revisions[-1]}")
    dev_root = development_branch_revisions[0]
    dev_tip = development_branch_revisions[-1]

    def branch_parent_revision(branch: bytes, revision_number: int):
        revisions = branches[branch]
        from bisect import bisect_left
        i = bisect_left(revisions, revision_number)
        if i<=0: return None
        return revisions[i-1]

    for branch, modified in modified_files_per_branch.items():
        SCAN_MARGIN = 3
        branch_revisions = branches[branch]
        first_rev = branch_revisions[0]
        tip_rev = branch_revisions[-1]
        scan_rev = branch_revisions[-SCAN_MARGIN:][0]
        nmodified = len(modified_files_per_branch[branch])
        target_branch = (
            b'branches/development-branch'
            if first_rev > dev_root and tip_rev < dev_tip else
            b'trunk'
        )
        print(f"{branch.decode()} {first_rev}-{tip_rev}, scanning from {scan_rev} in {target_branch.decode()}, {nmodified} files changed")

        @dataclass
        class Candidate:
            rev_number: int
            parent: int
            nshared: int
            notincommit: int
            notinmerge: int

            @staticmethod
            def create(branch: bytes, rev_number: int, merged_files: set[bytes]):
                commit_files = modified_rev_files(rev_number, branch)
                nshared = len(commit_files.intersection(merged_files))
                parent = branch_parent_revision(target_branch, rev_number)
                notinmerge = len(commit_files - merged_files)
                notincommit = len(merged_files - commit_files)
                return Candidate(
                    rev_number = rev_number,
                    nshared = nshared,
                    parent = parent,
                    notinmerge = notinmerge,
                    notincommit = notincommit,
                )

        candidate_revisions = [
            candidate
            for candidate in (
                Candidate.create(branch=target_branch, rev_number=rev_number, merged_files=modified_files_per_branch[branch])
                for rev_number in branches[target_branch]
                if rev_number >= scan_rev
            )
            if candidate.nshared
            #and candidate.notinmerge < candidate.nshared
        ]
        for candidate in candidate_revisions:
            print(
                f"\tRevision: {candidate.rev_number} (parent {candidate.parent})"
                f"\tto merge ( {candidate.notincommit} ( {candidate.nshared} ) {candidate.notinmerge} ) commit ")

        # TODO: In the target_branch, look for matchability of each revision geater than scan_rev
        # If there is no coincidence ignore the revision
        # If there is a coincidence, count matching files, and files in one side not in the other.
        # Output the merge revision candidate, is current parent and those three counts







