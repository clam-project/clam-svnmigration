
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

    branches = dict()

    for rev_number, rev in enumerate(dump.revisions):
        edited_branches = {
            branch for branch in (
                node_path_branch(node.fields[b'Node-path'])
                for node in rev.nodes
            )
            if branch is not None
        }
        if len(edited_branches) != 1:
            warn(f"Expected single branch revision {rev_number} but found: {b', '.join(edited_branches).decode()}")
            warn(f"{rev.properties.get(b'svn:log')}")
        for branch in edited_branches:
            branches.setdefault(branch, []).append(rev_number)

    for name, revisions in branches.items():
        print(name, revisions)







