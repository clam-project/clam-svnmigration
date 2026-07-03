import sys
from pathlib import Path

import typer

from .svndump import parse_svndump, dump_svndump


def preprocess(
    dump_file: Path = typer.Argument(..., help="Path to SVN dump file"),
):
    """Preprocess SVN dump: fix GraphicsViewNetworkCanvas branch paths."""
    data = open(dump_file, "rb").read()
    dump = parse_svndump(data)

    rev = dump.revisions[13369]
    print(f"=== Revision {rev.number} ===")
    print(rev.header.decode("latin-1"))
    print()
    for i, node in enumerate(rev.nodes):
        print(f"--- Node {i} ---")
        for k, v in node.fields.items():
            print(f"  {k.decode()}: {v.decode()}")
