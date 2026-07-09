
import sys
from pathlib import Path
from collections import OrderedDict
from consolemsg import step, warn, success
import typer
from .svndump import parse_svndump, dump_svndump, SvnNode
from os.path import commonprefix


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

    #for name, revisions in branches.items():
    #    print(name, revisions)

    ignored_branches = [
        b'branches/development-branch',
    ]

    modified_files_per_branch = dict()
    for branch, revisions in branches.items():
        if branch == b'trunk': continue
        if branch.startswith(b'tags'): continue
        if branch in ignored_branches: continue

        modified = set()
        for rev_num in revisions:
            rev = dump.revisions[rev_num]
            log = (rev.properties.get(b'svn:log') or b'<empty log>').decode()
            if 'manufactured' in log: continue
            modified |= {
                node.fields[b'Node-path'][len(branch) + 1:]
                for node in rev.nodes
                if node.fields[b'Node-path'].startswith(branch)
                and node.fields[b'Node-path'] != branch
            }

        if not modified:
            warn(f"Empty branch: {branch.decode()}")
            continue
        modified_files_per_branch[branch] = modified

    for name, files in modified_files_per_branch.items():
        print(name)
        for file in sorted(files):
            print(f'\t{file.decode()}')



